"""
Pipecat pipeline using the built-in Pipecat runner server.

Pipeline:
  transport.input() → raw_logger → latency_pre → STT → agg.user() → latency_mid → LLM → TTS → latency_post → transport.output() → agg.assistant()

Services:
  STT: OpenAI Whisper (streaming transcripts)
  LLM: Anthropic Claude (streaming tokens)
  TTS: OpenAI TTS (streaming audio chunks)
  VAD: Silero (barge-in / interruption handling)

Run:
  uv run python src/voice/pipeline.py
"""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path so `config` and `src` are importable
# when this file is run directly: `python src/voice/pipeline.py`
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Must be set before pipecat imports — suppresses NLTK 3.10 CWD import block
os.environ.setdefault("NLTK_DISABLE_IMPORT_SECURITY", "1")

from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    AudioRawFrame,
    LLMRunFrame,
    LLMTextFrame,
    TranscriptionFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.anthropic.llm import AnthropicLLMService, AnthropicLLMSettings
from pipecat.services.openai.stt import OpenAISTTService
from pipecat.services.openai.tts import OpenAITTSService
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams
from pipecat.workers.runner import WorkerRunner

from config.logger import get_logger
from config.settings import get_settings
from src.voice.latency import LatencyTracker
from src.voice.system_prompt import SYSTEM_PROMPT

load_dotenv(override=True)

app_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Frame observer processors
# ---------------------------------------------------------------------------


class LatencyObserver(FrameProcessor):
    """
    Inline latency observer injected into the pipeline.
    Observes frames passing through to stamp timestamps and log transcriptions:
      - VAD end-of-utterance (UserStoppedSpeakingFrame)
      - First STT partial & transcribed text (TranscriptionFrame)
      - First LLM text token (LLMTextFrame)
      - First TTS audio chunk (AudioRawFrame)
    """

    def __init__(self, tracker: LatencyTracker, **kwargs):
        super().__init__(**kwargs)
        self._tracker = tracker
        self._first_audio_seen = False

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, UserStoppedSpeakingFrame):
            app_logger.info("🗣️ User Stopped Speaking")
            self._first_audio_seen = False
            self._tracker.start_turn()

        elif isinstance(frame, TranscriptionFrame):
            app_logger.info(f"🗣️ User Said: '{frame.text}'")
            if self._tracker.current:
                self._tracker.current.record_stt_partial()

        elif isinstance(frame, LLMTextFrame):
            app_logger.info(f"🧠 LLM Said: '{frame.text}'")
            if self._tracker.current:
                self._tracker.current.record_llm_token()

        elif isinstance(frame, AudioRawFrame) and not self._first_audio_seen:
            app_logger.info("🔊 TTS Audio Chunk Received")
            self._first_audio_seen = True
            if self._tracker.current:
                self._tracker.current.record_tts_chunk()

        await self.push_frame(frame, direction)


class RawFrameLogger(FrameProcessor):
    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        app_logger.info(f"🔍 RAW FRAME: {type(frame).__name__} dir={direction}")
        await self.push_frame(frame, direction)


# ---------------------------------------------------------------------------
# Transport params for Pipecat runner
# ---------------------------------------------------------------------------

transport_params = {
    "websocket": lambda: FastAPIWebsocketParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        add_wav_header=False,
        serializer=ProtobufFrameSerializer(),
    ),
}


# ---------------------------------------------------------------------------
# Bot entrypoint
# ---------------------------------------------------------------------------


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    """Run the voice pipeline with the provided transport.

    Args:
        transport (BaseTransport): The transport to use for communication.
        runner_args: runner session arguments
    """
    settings = get_settings()
    tracker = LatencyTracker()

    # -- STT (OpenAI Whisper) -----------------------------------------------
    stt = OpenAISTTService(
        api_key=settings.OPENAI_API_KEY,
        settings=OpenAISTTService.Settings(
            model=settings.STT_MODEL,
        ),
    )

    # -- LLM (Anthropic Claude) ---------------------------------------------
    llm = AnthropicLLMService(
        api_key=settings.ANTHROPIC_API_KEY,
        settings=AnthropicLLMSettings(
            model=settings.LLM_MODEL,
            system_instruction=SYSTEM_PROMPT,
            max_tokens=256,
        ),
    )

    # -- TTS (OpenAI TTS) --------------------------------------------------
    tts = OpenAITTSService(
        api_key=settings.OPENAI_API_KEY,
        settings=OpenAITTSService.Settings(
            voice=settings.TTS_VOICE,
            model=settings.TTS_MODEL,
        ),
    )

    # -- Context / aggregators ---------------------------------------------
    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    # -- Latency observers -------------------------------------------------
    pre_obs = LatencyObserver(tracker, name="latency-pre")
    mid_obs = LatencyObserver(tracker, name="latency-mid")
    post_obs = LatencyObserver(tracker, name="latency-post")

    # -- Pipeline assembly -------------------------------------------------
    pipeline = Pipeline(
        [
            transport.input(),
            pre_obs,               # catches UserStoppedSpeakingFrame + TranscriptionFrame
            stt,
            user_aggregator,
            mid_obs,               # catches LLMTextFrame (tokens flowing to TTS)
            llm,
            tts,
            post_obs,              # catches AudioRawFrame (synthesised audio)
            transport.output(),
            assistant_aggregator,
        ]
    )

    # -- Worker ------------------------------------------------------------
    worker = PipelineWorker(
        pipeline,
        name="voice-agent",
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        idle_timeout_secs=runner_args.pipeline_idle_timeout_secs,
        enable_tracing=True,
        enable_turn_tracking=True,
    )

    @worker.rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        app_logger.info("Pipecat client ready.")
        context.add_message(
            {"role": "developer", "content": "Start by introducing yourself."}
        )
        await worker.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        app_logger.info("Pipecat Client connected")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        app_logger.info("Pipecat Client disconnected — cancelling worker")
        tracker.finalize()
        await worker.cancel()

    runner = WorkerRunner(handle_sigint=runner_args.handle_sigint)

    await runner.add_workers(worker)
    await runner.run()


async def bot(runner_args: RunnerArguments):
    """Main bot entry point compatible with Pipecat Cloud."""
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


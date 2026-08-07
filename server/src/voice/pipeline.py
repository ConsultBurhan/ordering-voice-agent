"""
Pipecat pipeline using the built-in Pipecat runner server.

Pipeline:
  transport.input() → raw_logger → latency_pre → STT → agg.user() → latency_mid → LLM → TTS → latency_post → transport.output() → agg.assistant()

Services:
  STT: ElevenLabs Realtime (streaming transcripts)
  LLM: OpenAI GPT-4o (streaming tokens) with Pipecat Flows tool-calling
  TTS: ElevenLabs TTS (streaming audio chunks)
  VAD: Silero (barge-in / interruption handling)

Ordering Flow (Pipecat Flows):
  Welcome → Browse Menu → Customize Item → Cart → Payment → Order Complete

Run:
  uv run python src/voice/pipeline.py
"""

import os
import sys
import uuid
from pathlib import Path

# Ensure project root is in sys.path so `config` and `src` are importable
# when this file is run directly: `python src/voice/pipeline.py`
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Must be set before pipecat imports — suppresses NLTK 3.10 CWD import block
os.environ.setdefault("NLTK_DISABLE_IMPORT_SECURITY", "1")

from dotenv import load_dotenv
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.flows import FlowManager
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
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService, CommitStrategy
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.transport import (
    SmallWebRTCTransport,
    TransportParams,
)
from pipecat.workers.runner import WorkerRunner
from langsmith.integrations.pipecat import configure_pipecat, set_thread_id
from config.logger import get_logger
from config.settings import get_settings
from src.voice.latency import LatencyTracker
from src.food_ordering_flow.menu import get_menu_payload
from src.food_ordering_flow.nodes import create_welcome_node
from src.food_ordering_flow.state import initial_state
from src.voice.menu_sync_processor import MenuSyncProcessor

# Load env vars first so LANGSMITH_* variables are available when configure_pipecat() runs
load_dotenv(override=True)

app_logger = get_logger(__name__)

# Install the LangSmith tracer and span processor once at startup.
# Each conversation gets its own thread via set_thread_id() inside run_bot().
configure_pipecat()


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


# ---------------------------------------------------------------------------
# Bot entrypoint
# ---------------------------------------------------------------------------


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    """Run the voice pipeline with the provided transport.

    Args:
        transport (BaseTransport): The transport to use for communication.
        runner_args: runner session arguments
    """
    # A unique ID per conversation — groups all pipeline spans into one LangSmith thread.
    conversation_id = str(uuid.uuid4())
    set_thread_id(conversation_id)
    app_logger.info(f"🔗 LangSmith thread: {conversation_id}")

    settings = get_settings()
    tracker = LatencyTracker()

    # -- STT (ElevenLabs Realtime) -----------------------------------------------
    stt = ElevenLabsRealtimeSTTService(
        api_key=settings.ELEVENLABS_API_KEY,
        language_code="eng",
        commit_strategy=CommitStrategy.VAD,
        include_timestamps=True,
        settings=ElevenLabsRealtimeSTTService.Settings(
            vad_silence_threshold_secs=0.6,
            vad_threshold=0.8,
        ),
    )

    # -- LLM (OpenAI GPT-4o) with function-calling for Pipecat Flows -------------
    llm = OpenAILLMService(
        api_key=settings.OPENAI_API_KEY,
        settings=OpenAILLMService.Settings(
            model=settings.LLM_MODEL,
            temperature=0.7,
            max_tokens=256,
            frequency_penalty=0.5,
        ),
    )

    # -- TTS (ElevenLabs) --------------------------------------------------
    tts = ElevenLabsTTSService(
        api_key=settings.ELEVENLABS_API_KEY,
        settings=ElevenLabsTTSService.Settings(
            voice="21m00Tcm4TlvDq8ikWAM",  # Rachel
        ),
    )

    # -- Context / aggregators ---------------------------------------------
    context = LLMContext()
    context_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )
    user_aggregator, assistant_aggregator = context_aggregator

    # -- Latency & Menu Sync observers --------------------------------------
    pre_obs = LatencyObserver(tracker, name="latency-pre")
    mid_obs = LatencyObserver(tracker, name="latency-mid")
    post_obs = LatencyObserver(tracker, name="latency-post")
    menu_sync = MenuSyncProcessor(name="menu-sync-processor")

    # -- Pipeline assembly -------------------------------------------------
    pipeline = Pipeline(
        [
            transport.input(),
            pre_obs,               # catches UserStoppedSpeakingFrame + TranscriptionFrame
            stt,
            user_aggregator,
            mid_obs,
            llm,
            menu_sync,             # catches LLMTextFrames & synchronises kiosk UI live
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

    # -- Pipecat Flows (ordering flow graph) --------------------------------
    flow_manager = FlowManager(
        llm=llm,
        context_aggregator=context_aggregator,
        worker=worker,
    )

    @worker.rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        app_logger.info("Pipecat client ready — initialising ordering flow.")

        menu_sync.rtvi = rtvi
        menu_sync.flow_manager = flow_manager

        # Set up fresh session state for this conversation
        flow_manager.state.clear()
        flow_manager.state.update(initial_state(session_id=conversation_id))

        # Start at the Welcome node
        await flow_manager.initialize(await create_welcome_node())

        # Push initial menu payload and initial state to web client
        try:
            await rtvi.send_server_message({
                "type": "init_menu_payload",
                "menu": get_menu_payload(),
                "state": flow_manager.state,
            })
        except Exception as e:
            app_logger.warning(f"Could not send init menu payload: {e}")

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
    webrtc_connection: SmallWebRTCConnection = runner_args.webrtc_connection

    transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
    )
    await run_bot(transport, runner_args)

"""
Pipecat voice pipeline for the Food Ordering Kiosk Agent using PipelineWorker.

Pipeline:
  transport.input() → STT → agg.user() → LLM → menu_sync → TTS → transport.output() → agg.assistant()

Services:
  STT: ElevenLabs Realtime (streaming transcripts)
  LLM: Anthropic Claude (AnthropicLLMService) with direct @tool_options function calling & prompt caching
  TTS: ElevenLabs TTS (streaming audio chunks)
  VAD: Silero (barge-in / interruption handling)

Run:
  uv run python main.py
"""

import os
import sys
import uuid
from pathlib import Path

# Ensure project root is in sys.path so `config` and `src` are importable
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Must be set before pipecat imports — suppresses NLTK CWD import block
os.environ.setdefault("NLTK_DISABLE_IMPORT_SECURITY", "1")

from dotenv import load_dotenv
from pipecat.audio.filters.rnnoise_filter import RNNoiseFilter
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService, CommitStrategy
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.anthropic.llm import AnthropicLLMService
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.transport import (
    SmallWebRTCTransport,
    TransportParams,
)
from pipecat.workers.runner import WorkerRunner
from langsmith.integrations.pipecat import configure_pipecat, set_thread_id
from pipecat.frames.frames import LLMMessagesAppendFrame
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from src.food_ordering_flow.state import session_manager
from src.food_ordering_flow.tools import ALL_TOOLS
from src.voice.menu_sync_processor import MenuSyncProcessor
from src.voice.system_prompt import SYSTEM_PROMPT
from config.logger import get_logger
from config.settings import get_settings



load_dotenv(override=True)

app_logger = get_logger(__name__)

configure_pipecat()


# ---------------------------------------------------------------------------
# Bot entrypoint
# ---------------------------------------------------------------------------


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    """Run the voice agent pipeline with PipelineWorker and AnthropicLLMService.

    Args:lec
        transport (BaseTransport): The transport to use for communication.
        runner_args: runner session arguments
    """
    conversation_id = str(uuid.uuid4())
    set_thread_id(conversation_id)
    app_logger.info(f"🔗 LangSmith thread: {conversation_id}")

    settings = get_settings()

    # -- STT (ElevenLabs Realtime) -----------------------------------------------
    stt = ElevenLabsRealtimeSTTService(
        api_key=settings.ELEVENLABS_API_KEY,
        language_code="eng",
        commit_strategy=CommitStrategy.VAD,
        include_timestamps=True,
        settings=ElevenLabsRealtimeSTTService.Settings(
            model=settings.STT_MODEL,
            vad_silence_threshold_secs=0.7,
            vad_threshold=0.8,
        ),
    )

    # -- LLM (claude haiku 4.5) -----------------------------------------------------
    llm = AnthropicLLMService(
        api_key=settings.ANTHROPIC_API_KEY,
        settings=AnthropicLLMService.Settings(
            model=settings.LLM_MODEL,
            enable_prompt_caching=True,
            temperature=0.7,
            max_tokens=256,
        ),
    )
    

    # -- TTS (ElevenLabs) -------------------------------------------------------
    tts = ElevenLabsTTSService(
        api_key=settings.ELEVENLABS_API_KEY,
        settings=ElevenLabsTTSService.Settings(
            model=settings.TTS_MODEL,
            voice="21m00Tcm4TlvDq8ikWAM",
        ),  # Rachel
    )

    # -- Real-time Menu Sync Observer ------------------------------------------
    menu_sync = MenuSyncProcessor(name="menu-sync-processor")

    # -- LLM Context & Aggregators ---------------------------------------------
    context = LLMContext(
        messages=[{"role": "system", "content": SYSTEM_PROMPT}],
        tools=ALL_TOOLS,
    )
    vad = SileroVADAnalyzer(
        # params=VADParams(
        #     confidence=0.7,
        #     start_secs=0.4,
        #     stop_secs=0.6,
        #     min_volume=0.5,
        # )
    )

    context_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=vad,
        ),
    )

    # -- Pipeline Assembly -----------------------------------------------------
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            menu_sync,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    # -- Pipeline Worker --------------------------------------------------------
    worker = PipelineWorker(
        pipeline,
        name="food-ordering-agent",
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
        app_logger.info("Pipecat client ready — initialising food ordering agent.")

        worker._rtvi = rtvi
        menu_sync.rtvi = rtvi
        menu_sync.worker = worker

        session_manager.reset(session_id=conversation_id)

        try:
            await rtvi.send_server_message({
                "type": "init_menu_payload",
                "menu": get_menu_payload(),
                "state": session_manager.state,
            })
        except Exception as e:
            app_logger.warning(f"Could not send init menu payload: {e}")

        await worker.queue_frame(
            LLMMessagesAppendFrame(
                messages=[{"role": "user", "content": "Greet the customer warmly and ask what they would like to order today."}],
                run_llm=True,
            )
        )


    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        app_logger.info("Pipecat Client connected")


    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        app_logger.info("Pipecat Client disconnected — cancelling worker")
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
            audio_in_sample_rate=16000,
            audio_in_filter=RNNoiseFilter(),
            audio_out_enabled=True,
            audio_out_sample_rate=24000,
            audio_out_bitrate=64000,
            audio_out_end_silence_secs=1,
        ),
    )
    await run_bot(transport, runner_args)

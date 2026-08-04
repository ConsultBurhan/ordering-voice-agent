"""
Per-turn latency tracker for the voice pipeline.
Measures: STT partial first, LLM token first, TTS audio chunk first, total round-trip.
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from config.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TurnLatency:
    turn_id: int
    vad_end_ts: float = field(default_factory=time.monotonic)

    stt_partial_ts: Optional[float] = None
    llm_token_ts: Optional[float] = None
    tts_chunk_ts: Optional[float] = None
    turn_end_ts: Optional[float] = None

    def record_stt_partial(self) -> None:
        if self.stt_partial_ts is None:
            self.stt_partial_ts = time.monotonic()

    def record_llm_token(self) -> None:
        if self.llm_token_ts is None:
            self.llm_token_ts = time.monotonic()

    def record_tts_chunk(self) -> None:
        if self.tts_chunk_ts is None:
            self.tts_chunk_ts = time.monotonic()

    def record_turn_end(self) -> None:
        self.turn_end_ts = time.monotonic()

    def _ms(self, ts: Optional[float]) -> str:
        if ts is None:
            return "—"
        return f"{(ts - self.vad_end_ts) * 1000:.0f}ms"

    def log_summary(self) -> None:
        logger.info(
            f"[LATENCY] Turn #{self.turn_id} | "
            f"STT-first: {self._ms(self.stt_partial_ts)} | "
            f"LLM-first-token: {self._ms(self.llm_token_ts)} | "
            f"TTS-first-chunk: {self._ms(self.tts_chunk_ts)} | "
            f"Total: {self._ms(self.turn_end_ts)}"
        )


class LatencyTracker:
    """Tracks latency across consecutive conversation turns."""

    def __init__(self) -> None:
        self._turn_count = 0
        self._current: Optional[TurnLatency] = None

    def start_turn(self) -> TurnLatency:
        """Call when VAD detects end-of-utterance."""
        if self._current is not None:
            self._current.log_summary()
        self._turn_count += 1
        self._current = TurnLatency(turn_id=self._turn_count)
        logger.debug(f"[LATENCY] Turn #{self._turn_count} started")
        return self._current

    @property
    def current(self) -> Optional[TurnLatency]:
        return self._current

    def finalize(self) -> None:
        """Call at end of session to flush any pending turn."""
        if self._current is not None:
            self._current.record_turn_end()
            self._current.log_summary()
            self._current = None

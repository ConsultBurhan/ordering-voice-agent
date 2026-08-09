"""
Utility helper functions for the food ordering kiosk flow.
"""

from typing import Any, Dict
from config.logger import get_logger

logger = get_logger(__name__)


async def send_rtvi_message(params: Any, payload: Dict[str, Any]) -> bool:
    """
    Session-isolated helper function to broadcast real-time RTVI server messages
    from function tools to the specific web kiosk client.

    Extracts the session-specific RTVI processor directly from tool invocation params.

    Args:
        params: Pipecat FunctionCallParams object passed to the tool.
        payload (Dict[str, Any]): Data dictionary to send to the client.

    Returns:
        bool: True if message was sent, False otherwise.
    """
    try:
        worker = getattr(params, "pipeline_worker", None)
        rtvi = getattr(worker, "_rtvi", None) or getattr(worker, "rtvi", None) if worker else None
        if rtvi:
            await rtvi.send_server_message(payload)
            return True
    except Exception as e:
        logger.warning(f"Could not send session RTVI message: {e}")
    return False

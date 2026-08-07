"""
Utility helper functions for the food ordering kiosk flow.
"""

from typing import Any, Dict

from config.logger import get_logger
from pipecat.flows import FlowManager

logger = get_logger(__name__)


async def send_rtvi_message(flow_manager: FlowManager, payload: Dict[str, Any]) -> bool:
    """
    Universal helper function to broadcast real-time RTVI server messages
    from backend tool/edge functions to the web kiosk client.

    Args:
        flow_manager (FlowManager): The active Pipecat FlowManager instance.
        payload (Dict[str, Any]): Data dictionary to send to the client.

    Returns:
        bool: True if message was sent, False otherwise.
    """
    try:
        worker = getattr(flow_manager, "worker", None) or getattr(flow_manager, "task", None)
        if worker and hasattr(worker, "rtvi") and worker.rtvi:
            await worker.rtvi.send_server_message(payload)
            return True
        logger.warning("Could not send RTVI message: worker/rtvi not available on flow_manager")
        return False
    except Exception as e:
        logger.warning(f"Could not send RTVI message: {e}")
        return False

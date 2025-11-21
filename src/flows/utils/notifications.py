"""Notification utilities for Prefect flows."""

import logging
from typing import Optional
from prefect import task

logger = logging.getLogger(__name__)


@task(name="log_warning")
def log_warning(message: str, context: Optional[dict] = None):
    """Log warning message.

    Args:
        message: Warning message
        context: Optional context dictionary
    """
    log_msg = f"WARNING: {message}"
    if context:
        log_msg += f" | Context: {context}"
    logger.warning(log_msg)
    print(f"⚠️  {log_msg}")


@task(name="log_error")
def log_error(message: str, context: Optional[dict] = None):
    """Log error message and fail flow.

    Args:
        message: Error message
        context: Optional context dictionary

    Raises:
        RuntimeError: Always raises to fail the flow
    """
    log_msg = f"ERROR: {message}"
    if context:
        log_msg += f" | Context: {context}"
    logger.error(log_msg)
    print(f"❌ {log_msg}")
    raise RuntimeError(log_msg)


@task(name="log_info")
def log_info(message: str, context: Optional[dict] = None):
    """Log info message.

    Args:
        message: Info message
        context: Optional context dictionary
    """
    log_msg = f"INFO: {message}"
    if context:
        log_msg += f" | Context: {context}"
    logger.info(log_msg)
    print(f"✓ {log_msg}")


# Future: Add Slack/email notification tasks
# @task(name="send_slack_alert")
# def send_slack_alert(message: str, channel: str):
#     """Send Slack notification."""
#     pass

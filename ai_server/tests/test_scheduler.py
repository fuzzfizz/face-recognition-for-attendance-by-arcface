"""Tests for the training scheduler background loop."""
import asyncio
import datetime
from unittest.mock import patch, MagicMock
import pytest

from app.main import run_training_scheduler

@pytest.mark.anyio
async def test_scheduler_no_times():
    # If TRAINING_SCHEDULE_TIMES is empty, it should return immediately
    with patch("app.main.TRAINING_SCHEDULE_TIMES", ""):
        # We can just run it; it should not loop infinitely
        await run_training_scheduler()

@pytest.mark.anyio
async def test_scheduler_time_matches():
    # Mock TRAINING_SCHEDULE_TIMES to "19:00"
    # Mock datetime.datetime.now() to return a time of 19:00
    # Mock process_pending_queue to verify it gets called
    # Mock asyncio.sleep to raise CancelledError so the infinite loop terminates
    
    mock_now = MagicMock()
    mock_now.strftime.return_value = "19:00"
    
    with patch("app.main.TRAINING_SCHEDULE_TIMES", "19:00"), \
         patch("datetime.datetime") as mock_datetime, \
         patch("app.services.training_service.process_pending_queue") as mock_process, \
         patch("asyncio.sleep", side_effect=asyncio.CancelledError) as mock_sleep:
        
        mock_datetime.now.return_value = mock_now
        
        with pytest.raises(asyncio.CancelledError):
            await run_training_scheduler()
            
        mock_process.assert_called_once()
        mock_sleep.assert_called_once_with(61)

@pytest.mark.anyio
async def test_scheduler_time_does_not_match():
    # Mock TRAINING_SCHEDULE_TIMES to "19:00"
    # Mock datetime.datetime.now() to return a time of 18:59
    # Mock process_pending_queue to verify it does NOT get called
    # Mock asyncio.sleep to raise CancelledError so the infinite loop terminates
    
    mock_now = MagicMock()
    mock_now.strftime.return_value = "18:59"
    
    with patch("app.main.TRAINING_SCHEDULE_TIMES", "19:00"), \
         patch("datetime.datetime") as mock_datetime, \
         patch("app.services.training_service.process_pending_queue") as mock_process, \
         patch("asyncio.sleep", side_effect=asyncio.CancelledError) as mock_sleep:
        
        mock_datetime.now.return_value = mock_now
        
        with pytest.raises(asyncio.CancelledError):
            await run_training_scheduler()
            
        mock_process.assert_not_called()
        mock_sleep.assert_called_once_with(20)

import datetime
from unittest.mock import MagicMock, Mock

import pytest

from core.config import LLMConfig, LLMProvider
from core.llm.base import BaseLLMClient


# Create a testable subclass of BaseLLMClient (renamed to avoid pytest collection)
class MockBaseLLMClient(BaseLLMClient):
    """Test implementation of BaseLLMClient for testing purposes."""
    
    def _init_client(self):
        """Override to avoid NotImplementedError."""
        self.client = Mock()


class TestBaseLLMClientRateLimiting:
    """Test cases for base LLM client functionality, especially rate limiting."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = LLMConfig(model="test-model", provider=LLMProvider.OPENAI, api_key="test-key")
        self.client = MockBaseLLMClient(self.config)

    @pytest.mark.parametrize(
        ("error_message", "expected_seconds"),
        [
            ("Please try again in 11.276s", 12.276),  # 11.276 + 1 buffer
            ("Please try again in 5s", 6),             # 5 + 1 buffer
            ("Please try again in 0.5s", 1.5),        # 0.5 + 1 buffer
            ("Please try again in 300s", 300),        # Capped at 300
            ("Please try again in 400s", 300),        # Capped at 300
            ("retry after 30 seconds", 31),           # 30 + 1 buffer
            ("Retry After 15 Seconds", 16),           # Case insensitive
            ("wait 45 seconds", 46),                  # Wait pattern
            ("Rate limit exceeded", 60),              # Default fallback
            ("Unknown error", 60),                    # Default fallback
        ],
    )
    def test_rate_limit_sleep_error_parsing(self, error_message, expected_seconds):
        """Test that base class can parse rate limit durations from error messages."""
        err = Exception(error_message)
        
        sleep_duration = self.client.rate_limit_sleep(err)
        
        assert sleep_duration is not None
        actual_seconds = sleep_duration.total_seconds()
        assert actual_seconds == expected_seconds, f"Expected {expected_seconds}s, got {actual_seconds}s"

    @pytest.mark.parametrize(
        ("wait_time", "expected_result"),
        [
            (None, None),                                           # No sleep needed
            (datetime.timedelta(seconds=30), 30),                  # Normal case
            (datetime.timedelta(hours=1, minutes=30), 3600),       # Capped at 1 hour
            (datetime.timedelta(hours=2), 3600),                   # Capped at 1 hour  
            (datetime.timedelta(seconds=-5), 5),                   # Negative -> 5s default
            (datetime.timedelta(seconds=0), None),                 # Zero -> None (no sleep needed)
            (datetime.timedelta(seconds=0.5), 1),                  # Sub-second -> 1s minimum
            (datetime.timedelta(minutes=10), 600),                 # 10 minutes -> warning but allowed
        ],
    )
    def test_validate_sleep_duration(self, wait_time, expected_result):
        """Test sleep duration validation with safety bounds."""
        result = self.client._validate_sleep_duration(wait_time, "test-provider")
        
        assert result == expected_result

    def test_validate_sleep_duration_logging(self, caplog):
        """Test that appropriate warnings are logged for edge cases."""
        # Test negative duration warning
        negative_time = datetime.timedelta(seconds=-10)
        self.client._validate_sleep_duration(negative_time, "test")
        assert "Invalid sleep duration" in caplog.text
        
        # Test excessive duration warning
        caplog.clear()
        excessive_time = datetime.timedelta(hours=2)
        self.client._validate_sleep_duration(excessive_time, "test")
        assert "exceeds 1 hour" in caplog.text
        
        # Test long duration warning
        caplog.clear()
        long_time = datetime.timedelta(minutes=10)
        self.client._validate_sleep_duration(long_time, "test")
        assert "Long sleep duration" in caplog.text

    def test_total_seconds_vs_seconds_behavior(self):
        """Test timedelta.seconds vs timedelta.total_seconds() behavior."""
        # Demonstrate the difference between .seconds and .total_seconds()
        wait_time = datetime.timedelta(hours=2, minutes=30, seconds=15)
        
        # For this duration, both are the same (no days involved)
        assert wait_time.seconds == 9015  # All seconds fit in seconds component
        assert wait_time.total_seconds() == 2*3600 + 30*60 + 15  # 9015 seconds
        
        # Show a case where they differ (with days)
        wait_time_with_days = datetime.timedelta(days=1, hours=2, seconds=30)
        assert wait_time_with_days.seconds == 7230  # Only hours+seconds part
        assert wait_time_with_days.total_seconds() == 24*3600 + 2*3600 + 30  # Full duration
        
        # Verify validation applies safety bounds
        result = self.client._validate_sleep_duration(wait_time, "test")
        assert result == 3600  # Capped at 1 hour

    def test_rate_limit_parsing_edge_cases(self):
        """Test edge cases in error message parsing."""
        # Empty string
        assert self.client.rate_limit_sleep(Exception("")).total_seconds() == 60
        
        # Multiple matches - should use first
        err = Exception("Please try again in 10s or retry after 20 seconds")
        assert self.client.rate_limit_sleep(err).total_seconds() == 11  # 10 + 1 buffer
        
        # Decimal precision
        err = Exception("Please try again in 1.5s")  
        assert self.client.rate_limit_sleep(err).total_seconds() == 2.5  # 1.5 + 1
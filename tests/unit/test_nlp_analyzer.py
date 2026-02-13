"""Unit tests for NLP analyzer module."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from meeting_processor.nlp import (
    ContentAnalyzer,
    MeetingSummary,
    KeyPhrase,
    ActionItem
)


@pytest.fixture
def mock_text_analytics():
    """Mock Azure Text Analytics client."""
    with patch('meeting_processor.nlp.analyzer.TextAnalyticsClient') as mock_client:
        yield mock_client


@pytest.fixture
def analyzer(mock_text_analytics):
    """Create a ContentAnalyzer instance with mocked client."""
    with patch('meeting_processor.nlp.analyzer.AzureKeyCredential'):
        return ContentAnalyzer(
            text_analytics_key="test_key",
            text_analytics_endpoint="https://test.endpoint.com",
            language="en"
        )


class TestKeyPhrase:
    """Test KeyPhrase dataclass."""

    def test_create_key_phrase(self):
        """Test creating a key phrase."""
        phrase = KeyPhrase(text="machine learning", score=0.95)
        
        assert phrase.text == "machine learning"
        assert phrase.score == 0.95


class TestActionItem:
    """Test ActionItem dataclass."""

    def test_create_action_item(self):
        """Test creating an action item."""
        item = ActionItem(
            text="Follow up with client",
            assignee="John",
            due_date="2026-02-20"
        )
        
        assert item.text == "Follow up with client"
        assert item.assignee == "John"
        assert item.due_date == "2026-02-20"

    def test_action_item_optional_fields(self):
        """Test action item with optional fields."""
        item = ActionItem(text="Send report")
        
        assert item.text == "Send report"
        assert item.assignee is None
        assert item.due_date is None


class TestMeetingSummary:
    """Test MeetingSummary dataclass."""

    def test_create_summary(self):
        """Test creating a meeting summary."""
        summary = MeetingSummary(
            key_phrases=[KeyPhrase("test", 0.9)],
            topics=["topic1", "topic2"],
            action_items=[ActionItem("task1")],
            sentiment={"positive": 0.8, "neutral": 0.2, "negative": 0.0},
            entities=[{"text": "Microsoft", "category": "Organization"}],
            summary_text="This is a summary"
        )
        
        assert len(summary.key_phrases) == 1
        assert len(summary.topics) == 2
        assert len(summary.action_items) == 1
        assert summary.summary_text == "This is a summary"

    def test_summary_to_dict(self):
        """Test converting summary to dictionary."""
        summary = MeetingSummary(
            key_phrases=[KeyPhrase("test", 0.9)],
            topics=["topic1"],
            action_items=[],
            sentiment={},
            entities=[],
            summary_text="Summary"
        )
        
        result = summary.to_dict()
        
        assert isinstance(result, dict)
        assert "key_phrases" in result
        assert "topics" in result
        assert "summary_text" in result


class TestContentAnalyzer:
    """Test ContentAnalyzer class."""

    def test_initialization(self, mock_text_analytics):
        """Test analyzer initialization."""
        with patch('meeting_processor.nlp.analyzer.AzureKeyCredential'):
            analyzer = ContentAnalyzer(
                text_analytics_key="test_key",
                text_analytics_endpoint="https://test.endpoint.com",
                language="en"
            )
            
            assert analyzer.text_analytics_key == "test_key"
            assert analyzer.language == "en"

    def test_extract_topics(self, analyzer):
        """Test extracting topics from key phrases."""
        key_phrases = [
            KeyPhrase("machine learning", 0.95),
            KeyPhrase("artificial intelligence", 0.90),
            KeyPhrase("machine learning", 0.85)  # Duplicate
        ]
        
        topics = analyzer._extract_topics(key_phrases)
        
        assert "machine learning" in topics
        assert "artificial intelligence" in topics
        assert len(topics) == 2  # No duplicates

    def test_extract_action_items(self, analyzer):
        """Test extracting action items from text."""
        text = """
        TODO: Review the documentation
        We need to schedule a follow-up meeting
        Action: Send the report to the team
        """
        
        action_items = analyzer._extract_action_items(text)
        
        assert len(action_items) > 0
        assert any("documentation" in item.text.lower() for item in action_items)

    def test_extract_action_items_no_matches(self, analyzer):
        """Test action item extraction with no matches."""
        text = "This is a simple text without action items."
        
        action_items = analyzer._extract_action_items(text)
        
        # Should return empty list or very few items
        assert isinstance(action_items, list)

    def test_generate_summary(self, analyzer):
        """Test generating a summary."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        key_phrases = [KeyPhrase("topic1", 0.9), KeyPhrase("topic2", 0.8)]
        topics = ["topic1", "topic2"]
        
        summary = analyzer._generate_summary(text, key_phrases, topics)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "topic1" in summary or "topic2" in summary

    def test_categorize_content(self, analyzer):
        """Test categorizing content."""
        text = "We discussed security and privacy concerns in detail."
        categories = ["security", "privacy", "performance"]
        
        scores = analyzer.categorize_content(text, categories)
        
        assert isinstance(scores, dict)
        assert "security" in scores
        assert "privacy" in scores
        assert scores["security"] > 0
        assert scores["privacy"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

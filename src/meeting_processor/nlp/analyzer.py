"""
NLP and Content Understanding module using Azure Text Analytics.

This module processes transcriptions to extract insights, key topics,
action items, and structured information.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class KeyPhrase:
    """Represents an extracted key phrase."""
    text: str
    score: float


@dataclass
class ActionItem:
    """Represents an identified action item."""
    text: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None


@dataclass
class MeetingSummary:
    """Summary of meeting content analysis."""
    key_phrases: List[KeyPhrase]
    topics: List[str]
    action_items: List[ActionItem]
    sentiment: Dict[str, float]
    entities: List[Dict[str, Any]]
    summary_text: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key_phrases": [asdict(kp) for kp in self.key_phrases],
            "topics": self.topics,
            "action_items": [asdict(ai) for ai in self.action_items],
            "sentiment": self.sentiment,
            "entities": self.entities,
            "summary_text": self.summary_text
        }


class ContentAnalyzer:
    """
    Analyzes transcribed content using Azure Text Analytics
    for content understanding and insight extraction.
    """

    def __init__(
        self,
        text_analytics_key: str,
        text_analytics_endpoint: str,
        language: str = "en"
    ):
        """
        Initialize Content Analyzer.

        Args:
            text_analytics_key: Azure Text Analytics API key
            text_analytics_endpoint: Azure Text Analytics endpoint URL
            language: Language code (e.g., 'en', 'es', 'fr')
        """
        self.text_analytics_key = text_analytics_key
        self.text_analytics_endpoint = text_analytics_endpoint
        self.language = language

        try:
            from azure.ai.textanalytics import TextAnalyticsClient
            from azure.core.credentials import AzureKeyCredential

            self.client = TextAnalyticsClient(
                endpoint=text_analytics_endpoint,
                credential=AzureKeyCredential(text_analytics_key)
            )
        except ImportError:
            logger.error(
                "Azure Text Analytics SDK not installed. "
                "Install with: pip install azure-ai-textanalytics"
            )
            raise

    def analyze_transcription(
        self,
        transcription_text: str,
        extract_action_items: bool = True
    ) -> MeetingSummary:
        """
        Analyze transcription text to extract insights.

        Args:
            transcription_text: Full text of the transcription
            extract_action_items: Whether to extract action items

        Returns:
            MeetingSummary with extracted insights
        """
        logger.info("Analyzing transcription content")

        documents = [transcription_text]

        # Extract key phrases
        key_phrases = self._extract_key_phrases(documents)

        # Perform sentiment analysis
        sentiment = self._analyze_sentiment(documents)

        # Extract entities
        entities = self._extract_entities(documents)

        # Extract topics (simplified - using key phrases as topics)
        topics = self._extract_topics(key_phrases)

        # Extract action items if requested
        action_items = []
        if extract_action_items:
            action_items = self._extract_action_items(transcription_text)

        # Generate summary
        summary_text = self._generate_summary(
            transcription_text,
            key_phrases,
            topics
        )

        return MeetingSummary(
            key_phrases=key_phrases,
            topics=topics,
            action_items=action_items,
            sentiment=sentiment,
            entities=entities,
            summary_text=summary_text
        )

    def _extract_key_phrases(self, documents: List[str]) -> List[KeyPhrase]:
        """Extract key phrases from documents."""
        try:
            response = self.client.extract_key_phrases(
                documents=documents,
                language=self.language
            )

            key_phrases = []
            for doc in response:
                if not doc.is_error:
                    for phrase in doc.key_phrases:
                        # Assign a simple score based on position (earlier = more important)
                        score = 1.0 - (len(key_phrases) * 0.05)
                        key_phrases.append(KeyPhrase(text=phrase, score=max(0.5, score)))

            logger.info(f"Extracted {len(key_phrases)} key phrases")
            return key_phrases[:20]  # Return top 20

        except Exception as e:
            logger.error(f"Failed to extract key phrases: {e}")
            return []

    def _analyze_sentiment(self, documents: List[str]) -> Dict[str, float]:
        """Analyze sentiment of documents."""
        try:
            response = self.client.analyze_sentiment(
                documents=documents,
                language=self.language,
                show_opinion_mining=True
            )

            sentiment_scores = {
                "positive": 0.0,
                "neutral": 0.0,
                "negative": 0.0,
                "overall": "neutral"
            }

            for doc in response:
                if not doc.is_error:
                    sentiment_scores["positive"] = doc.confidence_scores.positive
                    sentiment_scores["neutral"] = doc.confidence_scores.neutral
                    sentiment_scores["negative"] = doc.confidence_scores.negative
                    sentiment_scores["overall"] = doc.sentiment

            logger.info(f"Sentiment: {sentiment_scores['overall']}")
            return sentiment_scores

        except Exception as e:
            logger.error(f"Failed to analyze sentiment: {e}")
            return {"positive": 0.0, "neutral": 1.0, "negative": 0.0, "overall": "neutral"}

    def _extract_entities(self, documents: List[str]) -> List[Dict[str, Any]]:
        """Extract named entities from documents."""
        try:
            response = self.client.recognize_entities(
                documents=documents,
                language=self.language
            )

            entities = []
            for doc in response:
                if not doc.is_error:
                    for entity in doc.entities:
                        entities.append({
                            "text": entity.text,
                            "category": entity.category,
                            "subcategory": entity.subcategory,
                            "confidence": entity.confidence_score
                        })

            logger.info(f"Extracted {len(entities)} entities")
            return entities

        except Exception as e:
            logger.error(f"Failed to extract entities: {e}")
            return []

    def _extract_topics(self, key_phrases: List[KeyPhrase]) -> List[str]:
        """Extract main topics from key phrases."""
        # Simple topic extraction - group similar key phrases
        # In a production system, you might use more sophisticated topic modeling
        topics = []
        seen_topics = set()

        for phrase in key_phrases[:10]:  # Top 10 phrases as topics
            # Simple deduplication
            normalized = phrase.text.lower()
            if normalized not in seen_topics:
                topics.append(phrase.text)
                seen_topics.add(normalized)

        return topics

    def _extract_action_items(self, text: str) -> List[ActionItem]:
        """
        Extract action items from text using pattern matching.
        
        Looks for common action item patterns like:
        - "TODO:", "Action:", "Follow-up:"
        - Imperative sentences
        - Dates and assignments
        """
        action_items = []
        
        # Simple pattern matching for common action item indicators
        import re
        
        patterns = [
            r"(?:TODO|Action|Follow-up|Task):\s*(.+?)(?:\n|$)",
            r"(?:We need to|We should|Must|Will)\s+(.+?)(?:\.|,|\n|$)",
            r"(?:@\w+)\s+(?:will|to|should)\s+(.+?)(?:\.|,|\n|$)"
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                action_text = match.group(1).strip()
                if len(action_text) > 10:  # Filter out very short matches
                    action_items.append(ActionItem(text=action_text))

        logger.info(f"Extracted {len(action_items)} action items")
        return action_items[:10]  # Return top 10

    def _generate_summary(
        self,
        text: str,
        key_phrases: List[KeyPhrase],
        topics: List[str]
    ) -> str:
        """
        Generate a summary of the meeting.
        
        This is a simple implementation. For production, consider using
        Azure's abstractive summarization or OpenAI GPT models.
        """
        # Take first few sentences as a simple summary
        sentences = text.split(". ")
        summary_sentences = sentences[:3] if len(sentences) >= 3 else sentences

        summary = ". ".join(summary_sentences)
        if not summary.endswith("."):
            summary += "."

        # Add key topics
        if topics:
            summary += f"\n\nKey topics discussed: {', '.join(topics[:5])}"

        return summary

    def categorize_content(
        self,
        text: str,
        categories: List[str]
    ) -> Dict[str, float]:
        """
        Categorize content into predefined categories.
        
        Args:
            text: Text to categorize
            categories: List of category names
        
        Returns:
            Dictionary mapping categories to confidence scores
        """
        # Placeholder for custom classification
        # In production, you might train a custom model or use
        # Azure Custom Text Classification
        
        logger.info(f"Categorizing content into {len(categories)} categories")
        
        # Simple keyword-based categorization
        scores = {}
        text_lower = text.lower()
        
        for category in categories:
            # Count occurrences of category-related words
            count = text_lower.count(category.lower())
            scores[category] = min(1.0, count / 10.0)
        
        return scores

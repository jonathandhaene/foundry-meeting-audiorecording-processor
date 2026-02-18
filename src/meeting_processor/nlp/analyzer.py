"""
NLP and Content Understanding module using Azure Text Analytics.

This module processes transcriptions to extract insights, key topics,
action items, and structured information.  NLP sub-tasks run in parallel
using a thread pool for faster overall analysis.
"""

import logging
import re
import textwrap
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Azure SDK imports (can be mocked in tests)
try:
    from azure.ai.textanalytics import TextAnalyticsClient, ExtractiveSummaryAction, AbstractiveSummaryAction
    from azure.core.credentials import AzureKeyCredential
except ImportError:
    TextAnalyticsClient = None  # type: ignore
    ExtractiveSummaryAction = None  # type: ignore
    AbstractiveSummaryAction = None  # type: ignore
    AzureKeyCredential = None  # type: ignore

try:
    from azure.identity import DefaultAzureCredential
except ImportError:
    DefaultAzureCredential = None  # type: ignore

logger = logging.getLogger(__name__)

# Azure Text Analytics limits per document
MAX_CHARS_PER_DOC = 5120
MAX_CHARS_SUMMARIZATION = 125000


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
        d = {
            "key_phrases": [asdict(kp) for kp in self.key_phrases],
            "topics": self.topics,
            "action_items": [asdict(ai) for ai in self.action_items],
            "sentiment": self.sentiment,
            "entities": self.entities,
            "summary_text": self.summary_text,
        }
        # Attach per-segment sentiment if available
        if hasattr(self, "_segment_sentiments") and self._segment_sentiments:
            d["segment_sentiments"] = self._segment_sentiments
        return d


class ContentAnalyzer:
    """
    Analyzes transcribed content using Azure Text Analytics
    for content understanding and insight extraction.
    """

    def __init__(
        self,
        text_analytics_key: Optional[str] = None,
        text_analytics_endpoint: str = "",
        language: str = "en",
        use_managed_identity: bool = False,
    ):
        """
        Initialize Content Analyzer.

        Args:
            text_analytics_key: Azure Text Analytics API key (optional if using managed identity)
            text_analytics_endpoint: Azure Text Analytics endpoint URL
            language: Language code (e.g., 'en', 'es', 'fr')
            use_managed_identity: Use Azure AD managed identity instead of API key
        """
        self.text_analytics_key = text_analytics_key
        self.text_analytics_endpoint = text_analytics_endpoint
        self.language = language

        if TextAnalyticsClient is None:
            logger.error("Azure Text Analytics SDK not installed. "
                         "Install with: pip install azure-ai-textanalytics")
            raise ImportError("Azure Text Analytics SDK not available")

        if use_managed_identity:
            if DefaultAzureCredential is None:
                raise ImportError("azure-identity package is required for managed identity auth")
            credential = DefaultAzureCredential()
            logger.info("Using Azure AD managed identity for Text Analytics")
        else:
            if AzureKeyCredential is None:
                raise ImportError("Azure Text Analytics SDK not available")
            credential = AzureKeyCredential(text_analytics_key)

        self.client = TextAnalyticsClient(endpoint=text_analytics_endpoint, credential=credential)

    # ------------------------------------------------------------------
    # Helpers: chunk text so each piece fits API limits
    # ------------------------------------------------------------------
    @staticmethod
    def _chunk_text(text: str, max_chars: int = MAX_CHARS_PER_DOC) -> List[str]:
        """Split text into chunks that fit the per-document character limit."""
        if len(text) <= max_chars:
            return [text]

        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks: List[str] = []
        current = ""
        for sentence in sentences:
            if len(current) + len(sentence) + 1 > max_chars:
                if current:
                    chunks.append(current)
                # If a single sentence exceeds the limit, hard-wrap it
                if len(sentence) > max_chars:
                    for part in textwrap.wrap(sentence, max_chars):
                        chunks.append(part)
                    current = ""
                else:
                    current = sentence
            else:
                current = f"{current} {sentence}".strip() if current else sentence
        if current:
            chunks.append(current)
        return chunks if chunks else [text[:max_chars]]

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def analyze_transcription(
        self,
        transcription_text: str,
        extract_action_items: bool = True,
        segments: Optional[List[Dict[str, Any]]] = None,
        nlp_options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> MeetingSummary:
        """
        Analyze transcription text to extract insights.
        NLP sub-tasks run in parallel for faster results.

        Args:
            transcription_text: Full text of the transcription
            extract_action_items: Whether to extract action items
            segments: Optional list of transcription segments for per-segment sentiment
            nlp_options: Optional dict of NLP processing options
            progress_callback: Optional callback(task_name, status) for pipeline progress

        Returns:
            MeetingSummary with extracted insights
        """
        opts = nlp_options or {}
        enable_sentiment = opts.get("enable_sentiment", True)
        enable_key_phrases = opts.get("enable_key_phrases", True)
        enable_entities = opts.get("enable_entities", True)
        enable_action = opts.get("enable_action_items", True) and extract_action_items
        enable_summary = opts.get("enable_summary", True)
        summary_sentences = opts.get("summary_sentences", 6)
        max_key_phrases = opts.get("max_key_phrases", 20)
        per_segment_sentiment = opts.get("per_segment_sentiment", True)

        logger.info("Analyzing transcription content (%d chars) – parallel mode", len(transcription_text))

        # Chunk for operations that have low per-document limits
        chunks = self._chunk_text(transcription_text, MAX_CHARS_PER_DOC)
        logger.info("Split text into %d chunk(s) for key phrases / sentiment / entities", len(chunks))

        pcb = progress_callback or (lambda *_: None)

        # ------------------------------------------------------------------
        # Launch all independent NLP sub-tasks in parallel
        # ------------------------------------------------------------------
        futures = {}
        with ThreadPoolExecutor(max_workers=6, thread_name_prefix="nlp") as pool:
            if enable_key_phrases:
                pcb("key_phrases", "running")
                futures["key_phrases"] = pool.submit(self._extract_key_phrases, chunks, max_key_phrases)

            if enable_sentiment:
                pcb("sentiment", "running")
                futures["sentiment"] = pool.submit(self._analyze_sentiment, chunks)

            if enable_sentiment and per_segment_sentiment and segments:
                pcb("segment_sentiment", "running")
                futures["segment_sentiment"] = pool.submit(self._analyze_segment_sentiments, segments)

            if enable_entities:
                pcb("entities", "running")
                futures["entities"] = pool.submit(self._extract_entities, chunks)

            if enable_action:
                pcb("action_items", "running")
                futures["action_items"] = pool.submit(self._extract_action_items, transcription_text)

            if enable_summary:
                pcb("summary", "running")
                futures["summary"] = pool.submit(self._extract_summary, transcription_text, summary_sentences)

            # Collect results as each completes
            results: Dict[str, Any] = {}
            for future in as_completed(futures.values()):
                # Find which key this future belongs to
                for key, f in futures.items():
                    if f is future:
                        try:
                            results[key] = future.result()
                        except Exception as e:
                            logger.error("NLP sub-task '%s' failed: %s", key, e)
                            results[key] = None
                        pcb(key, "done")
                        break

        # ------------------------------------------------------------------
        # Assemble results (use defaults when a task was skipped or failed)
        # ------------------------------------------------------------------
        key_phrases = results.get("key_phrases") or []
        sentiment = results.get("sentiment") or {"positive": 0.0, "neutral": 1.0, "negative": 0.0, "overall": "neutral"}
        segment_sentiments = results.get("segment_sentiment") or []
        entities = results.get("entities") or []
        action_items = results.get("action_items") or []
        summary_text = results.get("summary") or ""
        topics = self._extract_topics(key_phrases)

        result = MeetingSummary(
            key_phrases=key_phrases,
            topics=topics,
            action_items=action_items,
            sentiment=sentiment,
            entities=entities,
            summary_text=summary_text,
        )
        result._segment_sentiments = segment_sentiments
        return result

    def _extract_key_phrases(self, documents: List[str], max_count: int = 20) -> List[KeyPhrase]:
        """Extract key phrases from (possibly chunked) documents."""
        try:
            response = self.client.extract_key_phrases(documents=documents, language=self.language)

            phrase_counts: Dict[str, int] = {}
            for doc in response:
                if not doc.is_error:
                    for phrase in doc.key_phrases:
                        norm = phrase.lower()
                        phrase_counts[norm] = phrase_counts.get(norm, 0) + 1

            # Sort by frequency, then build KeyPhrase list
            sorted_phrases = sorted(phrase_counts.items(), key=lambda x: -x[1])
            key_phrases = []
            for phrase_text, count in sorted_phrases:
                score = min(1.0, 0.5 + count * 0.1)
                key_phrases.append(KeyPhrase(text=phrase_text.title(), score=round(score, 2)))

            logger.info("Extracted %d unique key phrases", len(key_phrases))
            return key_phrases[:max_count]

        except Exception as e:
            logger.error(f"Failed to extract key phrases: {e}")
            return []

    def _analyze_sentiment(self, documents: List[str]) -> Dict[str, Any]:
        """Analyze sentiment across (possibly chunked) documents and average."""
        try:
            response = self.client.analyze_sentiment(
                documents=documents, language=self.language, show_opinion_mining=True,
            )

            totals = {"positive": 0.0, "neutral": 0.0, "negative": 0.0}
            count = 0
            for doc in response:
                if not doc.is_error:
                    totals["positive"] += doc.confidence_scores.positive
                    totals["neutral"] += doc.confidence_scores.neutral
                    totals["negative"] += doc.confidence_scores.negative
                    count += 1

            if count:
                for k in totals:
                    totals[k] = round(totals[k] / count, 3)

            dominant = max(totals, key=totals.get)
            result = {**totals, "overall": dominant}
            logger.info("Sentiment: %s (pos=%.2f, neu=%.2f, neg=%.2f)",
                        dominant, totals["positive"], totals["neutral"], totals["negative"])
            return result

        except Exception as e:
            logger.error(f"Failed to analyze sentiment: {e}")
            return {"positive": 0.0, "neutral": 1.0, "negative": 0.0, "overall": "neutral"}

    def _extract_entities(self, documents: List[str]) -> List[Dict[str, Any]]:
        """Extract and deduplicate named entities across chunked documents."""
        try:
            response = self.client.recognize_entities(documents=documents, language=self.language)

            seen: Dict[str, Dict[str, Any]] = {}
            for doc in response:
                if not doc.is_error:
                    for entity in doc.entities:
                        key = (entity.text.lower(), entity.category)
                        existing = seen.get(key)
                        if existing is None or entity.confidence_score > existing["confidence"]:
                            seen[key] = {
                                "text": entity.text,
                                "category": entity.category,
                                "subcategory": entity.subcategory,
                                "confidence": round(entity.confidence_score, 3),
                            }

            entities = sorted(seen.values(), key=lambda e: -e["confidence"])
            logger.info("Extracted %d unique entities", len(entities))
            return entities[:30]

        except Exception as e:
            logger.error("Failed to extract entities: %s", e)
            return []

    def _extract_topics(self, key_phrases: List[KeyPhrase]) -> List[str]:
        """Derive topics from the most frequent key phrases."""
        topics = []
        seen: set = set()
        for phrase in key_phrases[:10]:
            norm = phrase.text.lower()
            if norm not in seen:
                topics.append(phrase.text)
                seen.add(norm)
        return topics

    # ------------------------------------------------------------------
    # Action-item extraction (regex-based, broad patterns)
    # ------------------------------------------------------------------
    def _extract_action_items(self, text: str) -> List[ActionItem]:
        """
        Extract action items from meeting transcript text.

        Matches a broad set of conversational patterns:
        - Explicit markers: "TODO:", "Action:", "Follow-up:", "Next step:"
        - Commitments:  "I will …", "I'll …", "I'm going to …"
        - Requests:     "Can you …", "Could you …", "Please …"
        - Obligations:  "We need to …", "We should …", "We have to …"
        - Plans:        "Let's …", "We are going to …", "The plan is to …"
        - Deadlines:    "… by Monday", "… before next week"
        """
        action_items: List[ActionItem] = []
        seen_texts: set = set()

        patterns = [
            # Explicit markers
            r"(?:TODO|Action|Follow[\s-]?up|Next[\s-]?step|Task)[\s:]+(.+?)(?:\.|;|\n|$)",
            # Personal commitments
            r"(?:I will|I'll|I'm going to|I am going to)\s+(.+?)(?:\.|;|\n|$)",
            # Requests
            r"(?:Can you|Could you|Would you|Please)\s+(.+?)(?:\.|;|\?|\n|$)",
            # Group obligations
            r"(?:We need to|We should|We have to|We must|We ought to|We're going to|We will|We'll)\s+(.+?)(?:\.|;|\n|$)",
            # Suggestions / plans
            r"(?:Let's|Let us|The plan is to|The next step is to|Make sure to|Don't forget to|Remember to)\s+(.+?)(?:\.|;|\n|$)",
            # Assignments  (@name or "Name will/should")
            r"(?:@\w+|[A-Z][a-z]+)\s+(?:will|should|needs to|has to|is going to)\s+(.+?)(?:\.|;|\n|$)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                action_text = match.group(1).strip().rstrip(",;")
                # Skip very short or duplicate items
                if len(action_text) < 10:
                    continue
                norm = action_text.lower()
                if norm not in seen_texts:
                    seen_texts.add(norm)
                    action_items.append(ActionItem(text=action_text))

        logger.info("Extracted %d action items", len(action_items))
        return action_items[:15]

    # ------------------------------------------------------------------
    # Extractive summarization via Azure Text Analytics
    # ------------------------------------------------------------------
    def _extract_summary(self, text: str, max_sentence_count: int = 6) -> str:
        """
        Generate a summary using Azure Text Analytics extractive summarization.

        Falls back to a simple heuristic if the API call fails.
        """
        # Truncate to the summarization limit
        trimmed = text[:MAX_CHARS_SUMMARIZATION]

        # Try extractive summarization first
        try:
            poller = self.client.begin_analyze_actions(
                documents=[trimmed],
                actions=[ExtractiveSummaryAction(max_sentence_count=max_sentence_count)],
                language=self.language,
            )
            results = poller.result()
            for page in results:
                for result in page:
                    if not result.is_error:
                        sentences = [s.text for s in result.sentences]
                        if sentences:
                            summary = " ".join(sentences)
                            logger.info("Extractive summary generated (%d chars)", len(summary))
                            return summary
        except Exception as e:
            logger.warning("Extractive summarization failed, trying abstractive: %s", e)

        # Try abstractive summarization as fallback
        try:
            poller = self.client.begin_analyze_actions(
                documents=[trimmed],
                actions=[AbstractiveSummaryAction(sentence_count=4)],
                language=self.language,
            )
            results = poller.result()
            for page in results:
                for result in page:
                    if not result.is_error:
                        summaries = [s.text for s in result.summaries]
                        if summaries:
                            summary = " ".join(summaries)
                            logger.info("Abstractive summary generated (%d chars)", len(summary))
                            return summary
        except Exception as e:
            logger.warning("Abstractive summarization also failed: %s", e)

        # Last-resort heuristic: first few sentences + topic overview
        return self._fallback_summary(text)

    # ------------------------------------------------------------------
    # Per-segment sentiment analysis (D365-style)
    # ------------------------------------------------------------------
    def _analyze_segment_sentiments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for each transcription segment individually.

        Returns a list of dicts with start, end, speaker, sentiment label, and scores.
        Batches segments into groups of 10 (API limit) for efficiency.
        """
        results: List[Dict[str, Any]] = []
        batch_size = 10

        # Filter segments with non-empty text
        valid_segments = [
            (i, seg) for i, seg in enumerate(segments)
            if seg.get("text", "").strip()
        ]

        for batch_start in range(0, len(valid_segments), batch_size):
            batch = valid_segments[batch_start:batch_start + batch_size]
            texts = [seg.get("text", "")[:MAX_CHARS_PER_DOC] for _, seg in batch]

            try:
                response = self.client.analyze_sentiment(
                    documents=texts, language=self.language,
                )
                for (orig_idx, seg), doc in zip(batch, response):
                    if not doc.is_error:
                        results.append({
                            "index": orig_idx,
                            "start": seg.get("start", 0),
                            "end": seg.get("end", 0),
                            "speaker": seg.get("speaker", "Unknown"),
                            "sentiment": doc.sentiment,
                            "scores": {
                                "positive": round(doc.confidence_scores.positive, 3),
                                "neutral": round(doc.confidence_scores.neutral, 3),
                                "negative": round(doc.confidence_scores.negative, 3),
                            },
                        })
                    else:
                        results.append({
                            "index": orig_idx,
                            "start": seg.get("start", 0),
                            "end": seg.get("end", 0),
                            "speaker": seg.get("speaker", "Unknown"),
                            "sentiment": "neutral",
                            "scores": {"positive": 0.0, "neutral": 1.0, "negative": 0.0},
                        })
            except Exception as e:
                logger.warning("Per-segment sentiment batch failed: %s", e)
                for orig_idx, seg in batch:
                    results.append({
                        "index": orig_idx,
                        "start": seg.get("start", 0),
                        "end": seg.get("end", 0),
                        "speaker": seg.get("speaker", "Unknown"),
                        "sentiment": "neutral",
                        "scores": {"positive": 0.0, "neutral": 1.0, "negative": 0.0},
                    })

        logger.info("Per-segment sentiment: analyzed %d segments", len(results))
        return results

    def _fallback_summary(self, text: str) -> str:
        """Simple heuristic summary when Azure summarization is unavailable."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        # Pick up to 5 representative sentences (first 2, middle 1, last 2)
        picks: List[str] = []
        if len(sentences) >= 5:
            picks = sentences[:2] + [sentences[len(sentences) // 2]] + sentences[-2:]
        else:
            picks = sentences[:5]
        summary = " ".join(picks)
        if summary and not summary[-1] in ".!?":
            summary += "."
        return summary

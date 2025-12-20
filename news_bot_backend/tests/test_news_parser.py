# news_bot_backend/tests/test_news_parser.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from app.services.news_parser import (
    _make_utc_aware,
    _extract_topic_from_rss_entry,
    _normalize_topic_name,
    parse_news,
)


class TestMakeUtcAware:
    """Тесты для функции _make_utc_aware."""

    def test_make_utc_aware_with_naive_datetime(self):
        """Тест конвертации naive datetime в UTC-aware."""
        naive_dt = datetime(2025, 12, 20, 12, 0, 0)
        result = _make_utc_aware(naive_dt)

        assert result.tzinfo == timezone.utc
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 20

    def test_make_utc_aware_with_aware_datetime(self):
        """Тест что aware datetime остается без изменений."""
        aware_dt = datetime(2025, 12, 20, 12, 0, 0, tzinfo=timezone.utc)
        result = _make_utc_aware(aware_dt)

        assert result == aware_dt
        assert result.tzinfo == timezone.utc

    def test_make_utc_aware_with_none(self):
        """Тест что None возвращается как есть."""
        assert _make_utc_aware(None) is None


class TestExtractTopicFromRssEntry:
    """Тесты для функции _extract_topic_from_rss_entry."""

    def test_extract_topic_from_string_category(self):
        """Тест извлечения топика из строковой категории."""
        entry = Mock()
        entry.category = "Technology"

        result = _extract_topic_from_rss_entry(entry)
        assert result == "Technology"

    def test_extract_topic_from_list_category(self):
        """Тест извлечения топика из списка категорий."""
        entry = Mock()
        entry.category = ["Technology", "Science"]

        result = _extract_topic_from_rss_entry(entry)
        assert result == "Technology"

    def test_extract_topic_from_dict_category(self):
        """Тест извлечения топика из словаря категории."""
        entry = Mock()
        entry.category = [{"term": "Technology"}]

        result = _extract_topic_from_rss_entry(entry)
        assert result == "Technology"

    def test_extract_topic_from_tags(self):
        """Тест извлечения топика из тегов."""
        entry = Mock()
        entry.category = None
        entry.tags = [{"term": "Science"}]

        result = _extract_topic_from_rss_entry(entry)
        assert result == "Science"

    def test_extract_topic_from_subject(self):
        """Тест извлечения топика из subject."""
        entry = Mock()
        entry.category = None
        entry.tags = None
        entry.subject = "Politics"

        result = _extract_topic_from_rss_entry(entry)
        assert result == "Politics"

    def test_extract_topic_no_category(self):
        """Тест когда категория отсутствует."""
        entry = Mock()
        entry.category = None
        entry.tags = None
        entry.subject = None

        result = _extract_topic_from_rss_entry(entry)
        assert result is None


class TestNormalizeTopicName:
    """Тесты для функции _normalize_topic_name."""

    def test_normalize_simple_name(self):
        """Тест нормализации простого имени."""
        result = _normalize_topic_name("technology")
        assert result == "Technology"

    def test_normalize_with_spaces(self):
        """Тест нормализации имени с пробелами."""
        result = _normalize_topic_name("  technology  ")
        assert result == "Technology"

    def test_normalize_long_name(self):
        """Тест обрезки длинного имени до 50 символов."""
        long_name = "a" * 60
        result = _normalize_topic_name(long_name)
        assert len(result) == 50

    def test_normalize_empty_string(self):
        """Тест нормализации пустой строки."""
        result = _normalize_topic_name("")
        assert result == ""

    def test_normalize_title_case(self):
        """Тест что первая буква становится заглавной."""
        result = _normalize_topic_name("technology news")
        assert result == "Technology News"


class TestParseNews:
    """Тесты для функции parse_news."""

    @patch('app.services.news_parser.feedparser.parse')
    @patch('app.services.news_parser._process_article')
    def test_parse_rss_feed(self, mock_process, mock_feedparse):
        """Тест парсинга RSS фида."""
        # Мокируем RSS feed
        mock_feed = MagicMock()
        mock_entry = MagicMock()
        mock_entry.link = "https://example.com/article1"
        mock_entry.published_parsed = (2025, 12, 20, 12, 0, 0, 0, 0, 0)
        mock_entry.category = "Technology"
        mock_feed.entries = [mock_entry]
        mock_feedparse.return_value = mock_feed

        # Мокируем обработку статьи
        mock_process.return_value = {
            "title": "Test Article",
            "text": "Test content " * 20,  # > 100 символов
            "url": "https://example.com/article1",
            "published_at": datetime(2025, 12, 20, 12, 0, 0, tzinfo=timezone.utc),
            "topic": "Technology",
        }

        result = parse_news("https://example.com/rss", limit=1)

        assert len(result) == 1
        assert result[0]["title"] == "Test Article"
        assert result[0]["topic"] == "Technology"
        mock_process.assert_called_once()

    @patch('app.services.news_parser.feedparser.parse')
    def test_parse_empty_rss_feed(self, mock_feedparse):
        """Тест парсинга пустого RSS фида."""
        mock_feed = MagicMock()
        mock_feed.entries = []
        mock_feedparse.return_value = mock_feed

        result = parse_news("https://example.com/rss", limit=10)

        assert result == []

    @patch('app.services.news_parser.feedparser.parse')
    def test_parse_invalid_url(self, mock_feedparse):
        """Тест обработки невалидного URL."""
        mock_feedparse.side_effect = Exception("Connection error")

        result = parse_news("https://invalid-url.com/rss")

        assert result == []
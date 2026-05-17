# =============================================================================
# utils/smart_helpers.py
# Smart Helper Utilities for AI Voice Assistant
#
# Provides:
#   - Wikipedia smart fetch (no browser, disambiguation-safe)
#   - Web content summarizer (BeautifulSoup-based, cleans noise)
#   - RSS news headline fetcher
#   - Lightweight conversation memory (last 5 queries)
#   - "Explain Like I'm 5" simplifier
#   - Smart fallback intent detector
#
# Author: AI Voice Assistant Project
# =============================================================================

import re
import logging
import urllib.request
import xml.etree.ElementTree as ET
from typing import Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Conversation Memory (module-level singleton, last 5 entries)
# ---------------------------------------------------------------------------

_memory: list[dict] = []   # each entry: {"query": str, "response": str}

def memory_push(query: str, response: str) -> None:
    """Store a query/response pair; keep only the last 5."""
    _memory.append({"query": query, "response": response})
    if len(_memory) > 5:
        _memory.pop(0)

def memory_last() -> Optional[dict]:
    """Return the most recent memory entry, or None."""
    return _memory[-1] if _memory else None

def memory_all() -> list[dict]:
    """Return all stored memory entries."""
    return list(_memory)


# ---------------------------------------------------------------------------
# Wikipedia Smart Fetch
# ---------------------------------------------------------------------------

def wiki_summary(topic: str, sentences: int = 2) -> str:
    """
    Fetch a spoken-friendly Wikipedia summary for *topic*.

    Returns 1-2 sentences.  Handles disambiguation and missing pages
    gracefully — never opens the browser.

    Parameters
    ----------
    topic     : str  – the search term
    sentences : int  – how many sentences to return (default 2)
    """
    try:
        import wikipedia  # pip install wikipedia
        wikipedia.set_lang("en")
        try:
            summary = wikipedia.summary(topic, sentences=sentences, auto_suggest=True)
            # Strip parenthetical phonetics that sound awful in TTS
            summary = re.sub(r'\(\/[^)]+\/\)', '', summary)
            summary = re.sub(r'\s+', ' ', summary).strip()
            return summary
        except wikipedia.exceptions.DisambiguationError as e:
            # Pick the first reasonable option
            options = [o for o in e.options if "(" not in o][:3]
            options_str = ", ".join(options) if options else str(e.options[:3])
            return (
                f"'{topic}' could mean several things, such as {options_str}. "
                "Please be more specific."
            )
        except wikipedia.exceptions.PageError:
            return f"I couldn't find a Wikipedia page for '{topic}'."
    except ImportError:
        # Fallback: scrape Wikipedia REST API (no extra lib needed)
        return _wiki_rest_summary(topic, sentences)
    except Exception as e:
        logger.warning("wiki_summary error: %s", e)
        return f"I had trouble looking up '{topic}' on Wikipedia."


def _wiki_rest_summary(topic: str, sentences: int = 2) -> str:
    """Fallback Wikipedia summary via the REST API (no 3rd-party lib)."""
    import json
    slug = quote_plus(topic.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ARIA-VA/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        extract = data.get("extract", "")
        if not extract:
            return f"I couldn't find information about '{topic}' on Wikipedia."
        # Trim to requested sentence count
        sent_list = re.split(r'(?<=[.!?])\s+', extract.strip())
        result = " ".join(sent_list[:sentences])
        return result
    except Exception as e:
        logger.warning("_wiki_rest_summary error: %s", e)
        return f"I had trouble looking up '{topic}' on Wikipedia."


# ---------------------------------------------------------------------------
# Web Content Summarizer
# ---------------------------------------------------------------------------

_NOISE_TAGS = {"script", "style", "nav", "header", "footer",
               "aside", "form", "noscript", "iframe", "button", "input"}

def summarize_url(url: str, max_sentences: int = 5) -> str:
    """
    Fetch *url*, strip menus/ads/footers, and return up to *max_sentences*
    meaningful sentences as a clean spoken summary.

    Falls back gracefully if BeautifulSoup is not installed.
    """
    try:
        from bs4 import BeautifulSoup  # pip install beautifulsoup4
        req = urllib.request.Request(url, headers={"User-Agent": "ARIA-VA/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode(errors="replace")

        soup = BeautifulSoup(html, "html.parser")

        # Remove noisy elements
        for tag in soup.find_all(_NOISE_TAGS):
            tag.decompose()
        for tag in soup.find_all(True, {"class": re.compile(r"ad|menu|sidebar|cookie|banner|popup", re.I)}):
            tag.decompose()

        # Prefer article / main body
        body = (
            soup.find("article")
            or soup.find("main")
            or soup.find(id=re.compile(r"content|article|body", re.I))
            or soup.body
        )
        raw_text = body.get_text(separator=" ") if body else soup.get_text(separator=" ")

        # Clean whitespace
        raw_text = re.sub(r'\s+', ' ', raw_text).strip()

        # Split into sentences and filter very short ones
        sentences = re.split(r'(?<=[.!?])\s+', raw_text)
        good = [s.strip() for s in sentences if len(s.strip()) > 40]
        result = " ".join(good[:max_sentences])
        return result if result else "I couldn't extract meaningful content from that page."

    except ImportError:
        return _summarize_url_plain(url, max_sentences)
    except Exception as e:
        logger.warning("summarize_url error: %s", e)
        return "Sorry, I couldn't read that page right now."


def _summarize_url_plain(url: str, max_sentences: int = 5) -> str:
    """Plain-text fallback (no BeautifulSoup): strip HTML tags with regex."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ARIA-VA/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode(errors="replace")
        # Remove script/style blocks first
        html = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', html, flags=re.S | re.I)
        # Strip all remaining tags
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'&[a-z]+;', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        sentences = re.split(r'(?<=[.!?])\s+', text)
        good = [s.strip() for s in sentences if len(s.strip()) > 40]
        result = " ".join(good[:max_sentences])
        return result if result else "I couldn't extract meaningful content from that page."
    except Exception as e:
        logger.warning("_summarize_url_plain error: %s", e)
        return "Sorry, I couldn't read that page right now."


def summarize_topic(topic: str, max_sentences: int = 5) -> str:
    """
    High-level helper: summarize a topic by fetching its Wikipedia page.
    Suitable for 'tell me about X' / 'explain X' commands.
    """
    return wiki_summary(topic, sentences=max_sentences)


# ---------------------------------------------------------------------------
# "Explain Like I'm 5" Simplifier
# ---------------------------------------------------------------------------

# Simple word-level replacements to childify language
_ELI5_REPLACEMENTS = [
    (r'\butilize\b',          'use'),
    (r'\bsubsequently\b',     'then'),
    (r'\bnevertheless\b',     'but'),
    (r'\bfurthermore\b',      'also'),
    (r'\bconsequently\b',     'so'),
    (r'\bsignificant(?:ly)?\b','big'),
    (r'\bfundamental(?:ly)?\b','basic'),
    (r'\bimplemented\b',      'done'),
    (r'\bcomponent\b',        'part'),
    (r'\bcomponents\b',       'parts'),
    (r'\bfacilitate\b',       'help'),
    (r'\bdemonstrate\b',      'show'),
    (r'\bindividual\b',       'person'),
    (r'\bobtain\b',           'get'),
    (r'\bpurchase\b',         'buy'),
    (r'\brequire\b',          'need'),
    (r'\brequires\b',         'needs'),
    (r'\battempt\b',          'try'),
]

def explain_simple(topic: str) -> str:
    """
    Fetch a Wikipedia summary for *topic*, then simplify it to
    child-friendly language (2 short sentences max).
    """
    raw = wiki_summary(topic, sentences=2)
    if "couldn't" in raw or "could mean" in raw:
        return raw  # Already an error/disambiguation message

    text = raw
    for pattern, replacement in _ELI5_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.I)

    # Trim to 2 sentences after simplification
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    short = " ".join(sentences[:2])
    return f"Okay, simply put: {short}"


# ---------------------------------------------------------------------------
# Smart News Headline Fetcher (RSS-based, no API key needed)
# ---------------------------------------------------------------------------

_NEWS_RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.cnn.com/rss/edition.rss",
    "https://feeds.skynews.com/feeds/rss/home.xml",
]

def fetch_top_headlines(max_headlines: int = 3) -> str:
    """
    Pull top news headlines from RSS feeds (no API key).
    Returns a spoken-friendly string with up to *max_headlines* lines.
    """
    headlines: list[str] = []

    for feed_url in _NEWS_RSS_FEEDS:
        if len(headlines) >= max_headlines:
            break
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "ARIA-VA/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                raw_xml = resp.read().decode(errors="replace")
            root = ET.fromstring(raw_xml)
            # RSS items live at channel/item or directly under root
            items = root.findall(".//item")
            for item in items:
                title_el = item.find("title")
                if title_el is not None and title_el.text:
                    title = title_el.text.strip()
                    # Skip very short or "meta" titles
                    if len(title) > 15 and title.lower() not in ("rss", "feed", "news"):
                        headlines.append(title)
                if len(headlines) >= max_headlines:
                    break
        except Exception as e:
            logger.warning("RSS fetch failed for %s: %s", feed_url, e)
            continue

    if not headlines:
        return "I couldn't fetch the latest news right now. Please try again later."

    lines = [f"{i+1}. {h}" for i, h in enumerate(headlines[:max_headlines])]
    intro = f"Here are {len(lines)} top headlines. "
    return intro + " ".join(lines)


# ---------------------------------------------------------------------------
# Smart Fallback Intent Detector
# ---------------------------------------------------------------------------

_DEFINITION_PATTERNS = [
    r'\bwhat is\b', r'\bwhat are\b', r'\bdefine\b', r'\bdefinition of\b',
    r'\bmeaning of\b', r'\bwhat does .+ mean\b',
]
_EXPLANATION_PATTERNS = [
    r'\bexplain\b', r'\btell me about\b', r'\bwho is\b', r'\bwho was\b',
    r'\bhow does\b', r'\bhow do\b', r'\bwhat is .+ used for\b',
]
_CALC_PATTERNS = [
    r'\bcalculate\b', r'\bcompute\b', r'\bwhat is \d',
    r'\d+\s*[\+\-\*\/\^]\s*\d', r'\bhow much is\b',
    r'\bplus\b', r'\bminus\b', r'\btimes\b', r'\bdivided by\b',
]
_ELI5_PATTERNS = [
    r'\bexplain.{0,20}simple\b', r'\bexplain like\b', r'\beli5\b',
    r'\bin simple terms\b', r'\bsimply explain\b', r'\bsimple explanation\b',
]


def detect_fallback_intent(user_text: str) -> Optional[str]:
    """
    Analyse *user_text* and return a suggested intent string when
    the ML classifier returns 'unknown'. Returns None if no match.

    Possible return values: 'definition', 'explanation', 'calculator',
    'explain_simple', 'follow_up'
    """
    t = user_text.lower().strip()

    # Follow-up detection
    follow_up_triggers = ("tell me more", "explain that again", "more details",
                          "what else", "go on", "continue", "and then")
    if any(trigger in t for trigger in follow_up_triggers):
        return "follow_up"

    # Check ELI5 first (more specific than explanation)
    if any(re.search(p, t) for p in _ELI5_PATTERNS):
        return "explain_simple"

    if any(re.search(p, t) for p in _CALC_PATTERNS):
        return "calculator"

    if any(re.search(p, t) for p in _DEFINITION_PATTERNS):
        return "definition"

    if any(re.search(p, t) for p in _EXPLANATION_PATTERNS):
        return "explanation"

    return None


def extract_topic(user_text: str) -> str:
    """
    Strip common question prefixes and return the bare topic.
    E.g. "what is photosynthesis" → "photosynthesis"
         "explain black holes"    → "black holes"
    """
    t = user_text.strip()
    prefixes = [
        r'^(what is|what are|who is|who was|define|definition of|'
        r'meaning of|explain|tell me about|how does|how do|'
        r'simply explain|explain simply|eli5|explain like i.m 5|'
        r'in simple terms|give me a simple explanation of|'
        r'what does .+ mean)\s+',
    ]
    for pattern in prefixes:
        t = re.sub(pattern, '', t, flags=re.I).strip(" ?.,!")
    return t if t else user_text.strip()
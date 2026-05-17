# =============================================================================
# utils/actions.py
# Intent Action Execution Module  (Enhanced v2)
#
# Maps predicted intents to concrete actions the assistant performs.
# Each action function:
#   - Receives the original user text (for context where needed)
#   - Performs the action (open browser, compute, fetch data, etc.)
#   - Returns a human-readable response string for TTS + GUI display
#
# Supported intents:
#   greeting, time, date, open_youtube, open_google, web_search,
#   play_music, weather, calculator, about, joke, exit,
#   help, open_maps, news, wikipedia,
#   [NEW] read_web, explain_simple, definition, explanation, follow_up
#
# New in v2:
#   - Smart Web Reading Mode  (read / explain / tell me about → no browser)
#   - Website Content Summarizer
#   - Improved Wikipedia handler (wikipedia lib + REST fallback, no browser)
#   - "Explain Like I'm 5" mode  (explain_simple intent)
#   - Smart News Summarizer  (RSS headlines, no browser)
#   - Conversation Memory     (last 5 queries, follow-up aware)
#   - Better Intent Fallback  (detect definition / calc / explanation)
#
# Author: AI Voice Assistant Project
# =============================================================================

import webbrowser
import datetime
import json
import re
import math
import random
import logging
import urllib.request
from typing import Optional
from urllib.parse import quote_plus

# ── New helper module ────────────────────────────────────────────────────────
from utils.smart_helpers import (
    memory_push,
    memory_last,
    wiki_summary,
    summarize_topic,
    summarize_url,
    explain_simple as _eli5,
    fetch_top_headlines,
    detect_fallback_intent,
    extract_topic,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal HTTP helper
# ---------------------------------------------------------------------------

def _http_json(url: str, timeout: float = 10.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "ARIA-VA/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


# ---------------------------------------------------------------------------
# Weather helpers (kept from v1, city extractor updated below)
# ---------------------------------------------------------------------------

def _wmo_weather_desc(code: int) -> str:
    if code == 0:
        return "clear skies"
    if code in (1, 2, 3):
        return "partly cloudy skies"
    if code in (45, 48):
        return "foggy conditions"
    if code in (51, 53, 55, 56, 57):
        return "light rain or drizzle"
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "thunderstorms"
    return "mixed conditions"


FAMOUS_TRACKS = [
    ("Bohemian Rhapsody",      "Queen"),
    ("Billie Jean",            "Michael Jackson"),
    ("Shape of You",           "Ed Sheeran"),
    ("Blinding Lights",        "The Weeknd"),
    ("Rolling in the Deep",    "Adele"),
    ("Uptown Funk",            "Mark Ronson ft Bruno Mars"),
    ("Despacito",              "Luis Fonsi"),
    ("Thinking Out Loud",      "Ed Sheeran"),
    ("Smells Like Teen Spirit","Nirvana"),
    ("Hotel California",       "Eagles"),
    ("Sweet Child O Mine",     "Guns N Roses"),
    ("Someone Like You",       "Adele"),
]

# ---------------------------------------------------------------------------
# Predefined response pools
# ---------------------------------------------------------------------------

GREETING_RESPONSES = [
    "Hello! Great to see you. How can I help you today?",
    "Hi there! I'm your AI voice assistant. What can I do for you?",
    "Hey! I'm ready to assist. What do you need?",
    "Good to hear from you! How can I be of service?",
    "Greetings! I'm here and ready. What's on your mind?",
]

ABOUT_RESPONSES = [
    ("I'm an AI-powered voice assistant built with Python, Machine Learning, "
     "and Natural Language Processing. I can help you with time, web searches, "
     "music, calculations, and much more!"),
    ("My name is ARIA — Artificial Reasoning Intelligence Assistant. "
     "I was created using TF-IDF and Machine Learning to understand your voice commands."),
    ("I'm your intelligent voice companion. I use speech recognition and NLP "
     "to understand what you say, and ML to predict what you need."),
]

JOKES = [
    "Why don't scientists trust atoms? Because they make up everything!",
    "I told my computer I needed a break. Now it won't stop sending me Kit-Kat ads.",
    "Why did the AI go to therapy? It had too many deep learning issues.",
    "What do you call a fish without eyes? A fsh!",
    "Why did the programmer quit? Because they didn't get arrays.",
    "How do you comfort a JavaScript developer? You console them.",
    "Why was the math book sad? It had too many problems.",
    "I'm reading a book about anti-gravity. It's impossible to put down!",
]

BOSS_RESPONSES = [
    "My boss is Syed Ali Hassan, the mastermind behind my creation. He built me as part of the AI Lab project at the Department of Computer Science.",
    "Syed Ali Hassan is my creator and boss. Along with Muhammad Ahmad, he designed my intelligence, my voice, and everything you see in me.",
    "The person in charge is Syed Ali Hassan — student, developer, and the brain behind AIRA. I wouldn't exist without him.",
    "My boss goes by the name Syed Ali Hassan. He and his partner Muhammad Ahmad built me from scratch for their AI Lab project.",
    "I was created by Syed Ali Hassan and Muhammad Ahmad. Syed Ali is the boss — he gave me my purpose and my voice.",
]
# ===========================================================================
# ACTION FUNCTIONS — Existing (v1, unchanged signatures)
# ===========================================================================

def action_greeting(user_text: str) -> str:
    """Return a random greeting response."""
    return random.choice(GREETING_RESPONSES)


def action_time(user_text: str) -> str:
    """Return the current local time as a spoken string."""
    now = datetime.datetime.now()
    time_str = now.strftime("%I:%M %p")
    return f"The current time is {time_str}."


def action_date(user_text: str) -> str:
    """Return the current date as a spoken string."""
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    return f"Today is {date_str}."


def action_open_youtube(user_text: str) -> str:
    """Open YouTube in the default web browser."""
    try:
        webbrowser.open("https://www.youtube.com")
        logger.info("Opened YouTube.")
        return "Opening YouTube for you right now!"
    except Exception as e:
        logger.error("Failed to open YouTube: %s", e)
        return "Sorry, I couldn't open YouTube. Please check your browser."


def action_open_google(user_text: str) -> str:
    """Open Google in the default web browser."""
    try:
        webbrowser.open("https://www.google.com")
        logger.info("Opened Google.")
        return "Opening Google for you!"
    except Exception as e:
        logger.error("Failed to open Google: %s", e)
        return "Sorry, I couldn't open Google. Please check your browser."


def action_web_search(user_text: str) -> str:
    """
    Perform a Google web search for the query extracted from user_text.
    Strips common trigger phrases to isolate the search query.
    """
    trigger_phrases = [
        "search for", "search", "look up", "find", "google search",
        "google", "look for", "find me", "search the web for",
        "search on google",
    ]
    query = user_text.lower()
    for phrase in trigger_phrases:
        if query.startswith(phrase):
            query = query[len(phrase):].strip()
            break
    if not query:
        query = user_text

    try:
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(search_url)
        logger.info("Web search: '%s'", query)
        return f"Searching Google for: {query}"
    except Exception as e:
        logger.error("Web search failed: %s", e)
        return f"Sorry, I couldn't complete the search for '{query}'."



# ── YouTube Data API v3 key ──────────────────────────────────────────────────
# Get a free key at: https://console.cloud.google.com/apis/library/youtube.googleapis.com
# Quota cost: 100 units per search call; free tier = 10,000 units/day (~100 searches).
YOUTUBE_API_KEY = "PLACE YOUR ACTUAL API KEY RERE"   # ← replace with your key


def _youtube_top_video_id(query: str) -> Optional[str]:
    """
    Call the YouTube Data API v3 to find the video ID of the top search result.

    Returns the video ID string (e.g. 'dQw4w9WgXcQ') or None on any failure.
    Falls back gracefully so the old behaviour (search page) is used instead.
    """
    if not YOUTUBE_API_KEY or YOUTUBE_API_KEY.startswith("YOUR_"):
        return None  # Key not configured → skip API call

    encoded = quote_plus(query)
    url = (
        f"https://www.googleapis.com/youtube/v3/search"
        f"?part=snippet&q={encoded}&type=video&maxResults=1"
        f"&key={YOUTUBE_API_KEY}"
    )
    try:
        data = _http_json(url, timeout=8)
        items = data.get("items", [])
        if items:
            return items[0]["id"]["videoId"]
    except Exception as e:
        logger.warning("YouTube API search failed: %s", e)
    return None


def _extract_song_from_text(user_text: str) -> Optional[str]:
    """
    Try to pull a specific song or artist name from the user's command.
    E.g. 'play Blinding Lights' → 'Blinding Lights'
         'play something by Adele' → 'Adele'
         'play music' → None  (use random famous track)
    """
    t = user_text.strip()
    # Strip leading play/music triggers
    trigger_patterns = [
        r'^play\s+(?:me\s+)?(?:some\s+)?(?:music\s+(?:by|from)\s+)',   # "play music by X"
        r'^play\s+(?:me\s+)?(?:something\s+by\s+)',                     # "play something by X"
        r'^play\s+(?:me\s+)?(?:a\s+song\s+by\s+)',                     # "play a song by X"
        r'^play\s+(?:me\s+)?',                                          # "play me X" / "play X"
    ]
    for pattern in trigger_patterns:
        m = re.match(pattern, t, re.IGNORECASE)
        if m:
            remainder = t[m.end():].strip(" ?.,!")
            # Ignore generic words that mean "random music"
            generic = {"music", "song", "a song", "something", "anything",
                       "some music", "a tune", "tunes"}
            if remainder and remainder.lower() not in generic:
                return remainder
    return None


def action_play_music(user_text: str) -> str:
    """
    Auto-play music on YouTube.

    Strategy (in order):
      1. Extract a specific song/artist from the user's words.
      2. If nothing specific → pick a random famous track.
      3. Call YouTube Data API v3 to get the exact video ID.
      4. Open youtube.com/watch?v=ID  → video starts playing immediately.
      5. Fallback: if the API key is missing/broken, open the search-results
         page (old behaviour) so something always happens.
    """
    # ── Step 1 & 2: decide what to search for ───────────────────────────────
    specific = _extract_song_from_text(user_text)
    if specific:
        search_query = f"{specific} official audio"
        display_name = specific
    else:
        title, artist = random.choice(FAMOUS_TRACKS)
        search_query  = f"{artist} {title} official audio"
        display_name  = f"{title} by {artist}"

    logger.info("Play music: query=%r", search_query)

    # ── Step 3: resolve to a direct video ID via API ─────────────────────────
    video_id = _youtube_top_video_id(search_query)

    try:
        if video_id:
            # ── Step 4: open watch URL → auto-plays ──────────────────────────
            watch_url = f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
            webbrowser.open(watch_url)
            logger.info("Auto-playing video ID=%s", video_id)
            return f"Now playing {display_name} on YouTube!"
        else:
            # ── Step 5: fallback to search results page ───────────────────────
            fallback_url = (
                f"https://www.youtube.com/results"
                f"?search_query={quote_plus(search_query)}"
            )
            webbrowser.open(fallback_url)
            logger.info("Fallback: opened YouTube search for %r", search_query)
            return (
                f"I found {display_name} on YouTube. "
                "Click the top result to start playing — "
                "add a YouTube API key for full auto-play."
            )
    except Exception as e:
        logger.error("Play music failed: %s", e)
        return "Sorry, I could not open YouTube for music."


# ---------------------------------------------------------------------------
# Weather  (v1 preserved, import requests used here)
# ---------------------------------------------------------------------------

import requests  # noqa: E402  (kept here to match original structure)

OPENWEATHER_API_KEY = "REPLACE WITH YOUR API KEY"


def _city_from_weather_text(text: str) -> Optional[str]:
    """
    Extract city from phrases like:
      'weather in Lahore'  /  'what is weather in Islamabad'
    """
    match = re.search(r"weather\s+(?:in|at)\s+([a-zA-Z\s]+)", text.lower())
    if match:
        return match.group(1).strip().title()
    return None


def action_weather(user_text: str) -> str:
    """Fetch live weather using OpenWeatherMap API."""
    city = _city_from_weather_text(user_text) or "Rawalpindi"
    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
        )
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("cod") != 200:
            return f"I could not find weather information for {city}."

        temp_c    = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity  = data["main"]["humidity"]
        desc      = data["weather"][0]["description"]
        wind      = data["wind"]["speed"]
        temp_f    = (temp_c * 9 / 5) + 32

        return (
            f"In {city}, it is currently {round(temp_c)} degrees Celsius "
            f"which is about {round(temp_f)} degrees Fahrenheit, "
            f"with {desc}. "
            f"It feels like {round(feels_like)} degrees Celsius. "
            f"Humidity is {humidity} percent "
            f"and wind speed is around {round(wind)} meters per second."
        )
    except Exception as e:
        logger.error("Weather error: %s", e)
        return "Sorry, I could not fetch the weather right now."


def action_calculator(user_text: str) -> str:
    """
    Evaluate a simple arithmetic expression found in user_text.
    Supports: +, -, *, /, ^, %, and plain number words.
    """
    text = user_text.lower()
    replacements = {
        ' plus ':          ' + ',
        ' add ':           ' + ',
        ' minus ':         ' - ',
        ' subtract ':      ' - ',
        ' times ':         ' * ',
        ' multiplied by ': ' * ',
        ' multiply ':      ' * ',
        ' divided by ':    ' / ',
        ' divide ':        ' / ',
        ' over ':          ' / ',
        ' to the power of ':' ** ',
        ' squared':        ' ** 2',
        ' cubed':          ' ** 3',
        ' percent of ':    ' / 100 * ',
    }
    for word, symbol in replacements.items():
        text = text.replace(word, symbol)

    expr_match = re.search(r'[\d\s\+\-\*\/\.\(\)\%\^]+', text)
    if not expr_match:
        return "I couldn't find a calculation in your request. Please say something like 'calculate 5 plus 3'."

    expr = expr_match.group().strip().replace('^', '**')
    try:
        allowed_names = {
            "__builtins__": {},
            "abs": abs, "round": round, "math": math,
        }
        result = eval(compile(expr, "<string>", "eval"), allowed_names)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        elif isinstance(result, float):
            result = round(result, 4)
        return f"The result of {expr.strip()} is {result}."
    except ZeroDivisionError:
        return "I can't divide by zero!"
    except Exception as e:
        logger.warning("Calculator eval error: %s | expr='%s'", e, expr)
        return "I couldn't calculate that. Please try rephrasing your math question."


def action_about(user_text: str) -> str:
    """Return a random self-description of the assistant."""
    return random.choice(ABOUT_RESPONSES)
def action_boss(user_text: str) -> str:
    """Return a random response about the boss/creator."""
    return random.choice(BOSS_RESPONSES)

def action_joke(user_text: str) -> str:
    """Return a random joke."""
    return random.choice(JOKES)


def action_exit(user_text: str) -> str:
    """Return a farewell message before the application closes."""
    farewells = [
        "Goodbye! Have a wonderful day!",
        "See you later! Take care!",
        "Farewell! It was great chatting with you!",
        "Bye! Come back anytime you need help!",
    ]
    return random.choice(farewells)


def action_unknown(user_text: str) -> str:
    """
    Improved fallback: try to detect definition/explanation/calculation
    intent before giving up. Falls through to generic responses only if
    nothing matches.
    """
    detected = detect_fallback_intent(user_text)
    if detected == "follow_up":
        return action_follow_up(user_text)
    if detected == "explain_simple":
        return action_explain_simple(user_text)
    if detected == "calculator":
        return action_calculator(user_text)
    if detected in ("definition", "explanation"):
        return action_read_web(user_text)

    fallbacks = [
        "I'm sorry, I didn't quite understand that. Could you rephrase?",
        "Hmm, I'm not sure what you mean. Could you try again?",
        "I didn't catch that. Could you say it differently?",
        "I'm still learning! Could you rephrase that for me?",
    ]
    return random.choice(fallbacks)


def action_help(user_text: str) -> str:
    """Short, TTS-friendly list of what the assistant can do."""
    return (
        "Here is what I can do. Ask for the time or date. Open YouTube, Google, "
        "Maps. Search the web, look something up on Wikipedia, check weather, "
        "play music, do math, hear a joke, or ask who I am. "
        "Say 'tell me about' or 'explain' any topic and I will read it aloud. "
        "Say 'explain simply' for a child-friendly version. "
        "Say 'latest news' to hear top headlines. "
        "Say goodbye when you are done."
    )


def action_open_maps(user_text: str) -> str:
    """Open Google Maps for an optional place query."""
    t   = user_text.strip()
    low = t.lower()
    query = ""
    for phrase in (
        "directions to ", "map of ", "maps for ",
        "open google maps ", "open maps ", "google maps ",
        "show map of ",
    ):
        if phrase in low:
            idx = low.index(phrase) + len(phrase)
            query = t[idx:].strip(" ?.,!")
            break
    if not query:
        query = t
        for strip in (
            "open maps", "google maps", "show map",
            "open google map", "maps please", "launch maps",
        ):
            if low.startswith(strip):
                query = t[len(strip):].strip(" ?.,!")
                break
    if not query or query.lower() in ("here", "maps", "map", "google maps", "google map"):
        try:
            webbrowser.open("https://www.google.com/maps")
            logger.info("Opened Google Maps (home)")
            return "Opening Google Maps."
        except Exception as e:
            logger.error("Maps open failed: %s", e)
            return "Sorry, I could not open Maps."
    try:
        url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"
        webbrowser.open(url)
        logger.info("Opened Google Maps for query=%r", query)
        return f"Opening maps for {query}."
    except Exception as e:
        logger.error("Maps open failed: %s", e)
        return "Sorry, I could not open Maps."


# ===========================================================================
# ACTION FUNCTIONS — New (v2)
# ===========================================================================

# ---------------------------------------------------------------------------
# [NEW] Smart Wikipedia handler  — NO browser, disambiguation-safe
# ---------------------------------------------------------------------------

def action_wikipedia(user_text: str) -> str:
    """
    Fetch a 2-sentence spoken-friendly Wikipedia summary.
    Does NOT open the browser. Handles disambiguation + missing pages.
    """
    topic = extract_topic(user_text)
    logger.info("Wikipedia lookup for topic=%r", topic)
    summary = wiki_summary(topic, sentences=2)
    return summary


# ---------------------------------------------------------------------------
# [NEW] Smart Web Reading Mode  — read / explain / tell me about
# ---------------------------------------------------------------------------

def action_read_web(user_text: str) -> str:
    """
    When the user wants to 'read', 'explain', or 'tell me about' a topic,
    fetch and return the first 2-3 spoken-friendly sentences from Wikipedia
    without opening any browser.
    """
    topic = extract_topic(user_text)
    logger.info("Read-web request for topic=%r", topic)
    summary = wiki_summary(topic, sentences=3)
    return summary


# ---------------------------------------------------------------------------
# [NEW] Website Content Summarizer  — action_summarize_url
# ---------------------------------------------------------------------------

def action_summarize_url(user_text: str) -> str:
    """
    Extract a URL from user_text and return a clean 5-line summary of the
    page content. Strips menus, ads, and footer noise.

    If no URL is found, treat the remaining text as a topic and summarize
    from Wikipedia instead.
    """
    url_match = re.search(r'https?://[^\s]+', user_text)
    if url_match:
        url = url_match.group(0)
        logger.info("Summarizing URL: %s", url)
        return summarize_url(url, max_sentences=5)
    else:
        topic = extract_topic(user_text)
        logger.info("No URL found; summarizing topic=%r via Wikipedia", topic)
        return summarize_topic(topic, max_sentences=5)


# ---------------------------------------------------------------------------
# [NEW] "Explain Like I'm 5" Mode
# ---------------------------------------------------------------------------

def action_explain_simple(user_text: str) -> str:
    """
    Return a child-friendly 2-sentence explanation of any topic by
    fetching and simplifying a Wikipedia summary.
    """
    topic = extract_topic(user_text)
    logger.info("ELI5 request for topic=%r", topic)
    return _eli5(topic)


# ---------------------------------------------------------------------------
# [NEW] Smart News Summarizer  — RSS headlines, no browser
# ---------------------------------------------------------------------------

def action_news(user_text: str) -> str:
    """
    Fetch the top 3 news headlines from RSS feeds and return them as a
    spoken list. Does NOT open Google News in the browser.
    """
    logger.info("Fetching top headlines via RSS")
    return fetch_top_headlines(max_headlines=3)


# ---------------------------------------------------------------------------
# [NEW] Conversation Memory — follow-up handler
# ---------------------------------------------------------------------------

def action_follow_up(user_text: str) -> str:
    """
    Handle follow-up queries like 'tell me more' or 'explain that again'
    using the last item stored in conversation memory.
    """
    last = memory_last()
    if last is None:
        return "I don't have anything stored from our conversation yet. What would you like to know?"

    # Re-summarise the original topic with more sentences
    prev_query = last["query"]
    topic = extract_topic(prev_query)
    logger.info("Follow-up: re-fetching topic=%r", topic)
    return wiki_summary(topic, sentences=4)


# ---------------------------------------------------------------------------
# [NEW] Definition intent  (alias for read_web with a definition framing)
# ---------------------------------------------------------------------------

def action_definition(user_text: str) -> str:
    """
    Return a short definition-style Wikipedia snippet for the topic.
    (Triggered by 'define X', 'what is X', 'meaning of X' etc.)
    """
    topic = extract_topic(user_text)
    logger.info("Definition request for topic=%r", topic)
    summary = wiki_summary(topic, sentences=2)
    return summary


# ---------------------------------------------------------------------------
# [NEW] Explanation intent  (alias for read_web with 3 sentences)
# ---------------------------------------------------------------------------

def action_explanation(user_text: str) -> str:
    """
    Return a slightly longer Wikipedia explanation (3 sentences).
    (Triggered by 'explain X', 'how does X work' etc.)
    """
    return action_read_web(user_text)


# ===========================================================================
# Keyword router (pre-classifier safety net)
# ===========================================================================

def _route_keywords(user_text: str) -> Optional[str]:
    """
    Handle common phrases even when the classifier returns 'unknown'.
    Evaluates BEFORE the intent dispatch table.
    """
    t = user_text.lower().strip()
    if not t:
        return None

    # Help queries
    help_triggers = (
        "what can you do", "what do you do", "list your commands",
        "what commands", "your capabilities", "list commands",
        "show commands", "how do i use you", "voice commands",
    )
    if any(h in t for h in help_triggers):
        return action_help(user_text)

    # Follow-up
    follow_up_triggers = (
        "tell me more", "explain that again", "more details",
        "what else", "go on", "continue about",
    )
    if any(trigger in t for trigger in follow_up_triggers):
        return action_follow_up(user_text)

    # ELI5
    eli5_triggers = (
        "explain simply", "explain like i'm 5", "explain like i am 5",
        "eli5", "in simple terms", "simple explanation",
    )
    if any(e in t for e in eli5_triggers):
        return action_explain_simple(user_text)

    # Read / explain / tell me about → Smart Web Reading (no browser)
    read_triggers = (
        "tell me about", "read about", "what is ", "who is ",
        "who was ", "explain ", "describe ",
    )
    if any(t.startswith(rt) or f" {rt}" in t for rt in read_triggers):
        # Guard against short/ambiguous phrases
        topic = extract_topic(user_text)
        if topic and len(topic) > 2:
            return action_read_web(user_text)

    # Wikipedia explicit
    if "wikipedia" in t or t.startswith("wiki ") or " on wikipedia" in t:
        return action_wikipedia(user_text)

    # Maps
    map_triggers = (
        "open maps", "google maps", "show map",
        "open google map", "directions to", "map of",
    )
    if any(m in t for m in map_triggers):
        return action_open_maps(user_text)

    # News
    news_triggers = (
        "open news", "latest news", "breaking news",
        "news headlines", "google news", "show news", "headline news",
        "top headlines", "what's in the news",
    )
    if any(m in t for m in news_triggers):
        return action_news(user_text)

    # Summarize URL
    if re.search(r'https?://', t):
        return action_summarize_url(user_text)

    return None


# ===========================================================================
# Intent → Action dispatch table
# ===========================================================================

INTENT_ACTIONS: dict[str, callable] = {
    # ── Original intents ────────────────────────────────────────────────────
    "greeting":      action_greeting,
    "time":          action_time,
    "date":          action_date,
    "open_youtube":  action_open_youtube,
    "open_google":   action_open_google,
    "web_search":    action_web_search,
    "play_music":    action_play_music,
    "weather":       action_weather,
    "calculator":    action_calculator,
    "about":         action_about,
    "joke":          action_joke,
    "boss":          action_boss, 
    "exit":          action_exit,
    "help":          action_help,
    "open_maps":     action_open_maps,
    "news":          action_news,           # ← now returns RSS headlines
    "wikipedia":     action_wikipedia,      # ← now silent (no browser)
    # ── New intents (v2) ────────────────────────────────────────────────────
    "read_web":      action_read_web,
    "summarize_url": action_summarize_url,
    "explain_simple":action_explain_simple,
    "definition":    action_definition,
    "explanation":   action_explanation,
    "follow_up":     action_follow_up,
}


def execute_action(intent: str, user_text: str) -> str:
    """
    Look up and execute the action function for the given intent.

    Flow:
        1. Keyword router  (catches obvious patterns early)
        2. Intent dispatch table  (ML-predicted label)
        3. Smart fallback detector  (rescues 'unknown' intents)
        4. Generic fallback

    Stores every query/response pair in conversation memory for follow-ups.

    Parameters
    ----------
    intent    : str – The predicted intent label (e.g. 'greeting').
    user_text : str – The original user utterance.

    Returns
    -------
    str – The assistant's response text.
    """
    # 1. Keyword router  (always checked first)
    routed = _route_keywords(user_text)
    if routed is not None:
        logger.info("Keyword route handled utterance")
        memory_push(user_text, routed)
        return routed

    # 2. Intent dispatch
    action_fn = INTENT_ACTIONS.get(intent)
    if action_fn:
        logger.info("Executing action for intent='%s'", intent)
        response = action_fn(user_text)
        memory_push(user_text, response)
        return response

    # 3. Smart fallback — try to rescue unknown intent
    detected = detect_fallback_intent(user_text)
    if detected:
        logger.info("Smart fallback detected intent='%s'", detected)
        rescue_fn = INTENT_ACTIONS.get(detected, action_unknown)
        response = rescue_fn(user_text)
        memory_push(user_text, response)
        return response

    # 4. Generic fallback
    response = action_unknown(user_text)
    memory_push(user_text, response)
    return response


# ===========================================================================
# Quick self-test
# ===========================================================================
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    tests = [
        # Original intents
        ('greeting',   'hello'),
        ('time',       'what time is it'),
        ('date',       'what is today'),
        ('calculator', 'what is 25 plus 7'),
        ('calculator', 'calculate 10 times 5'),
        ('web_search', 'search for machine learning'),
        ('joke',       'tell me a joke'),
        # New intents
        ('wikipedia',     'who is Albert Einstein'),
        ('explain_simple','explain black holes simply'),
        ('news',          'latest news'),
        ('read_web',      'tell me about the moon'),
        ('follow_up',     'tell me more'),
        # Fallback rescue
        ('unknown_xyz', 'what is photosynthesis'),
        ('unknown_xyz', 'blah blah'),
    ]
    for intent, text in tests:
        response = execute_action(intent, text)
        print(f"[{intent}] '{text}'\n  → {response}\n")
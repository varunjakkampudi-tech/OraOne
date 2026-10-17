"""Pure TwiML builders for the voice agent.

Every function returns an XML string and touches no I/O, so the telephony
rules can be tested without Twilio or a database. All text (caller-facing
prompts, model answers, configured numbers) passes through
``xml.sax.saxutils.escape`` so nothing can inject markup or extra verbs.
"""

from __future__ import annotations

import re
from xml.sax.saxutils import escape

DEFAULT_VOICE = "alice"
MAX_ANSWER_CHARS = 600

GREETING_TEXT = "Hello, thanks for calling. How can I help you today?"
RETRY_TEXT = "Sorry, I didn't catch that. Could you say it again?"
SILENT_GOODBYE_TEXT = "I haven't heard anything, so I'll end the call. Goodbye."
ERROR_TEXT = "Sorry, something went wrong on our side. Please try again later. Goodbye."
UNAVAILABLE_TEXT = "Sorry, this number is not available right now. Goodbye."
OPT_OUT_TEXT = "You have been removed from our calling list. Goodbye."
HANDOFF_CONNECT_TEXT = "I'm connecting you with a member of our team now. One moment."
HANDOFF_UNAVAILABLE_TEXT = (
    "Sorry, I can't connect you to a person right now. "
    "Please try again later or send us a message in writing. Goodbye."
)

_XML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>'
_SENTENCE_END = re.compile(r"[.!?](?=\s|$)")
_WHITESPACE = re.compile(r"\s+")
_MARKDOWN_NOISE = re.compile(r"[*#`]")


def _text(value: str | None) -> str:
    return escape(value or "")


def _attr(value: str) -> str:
    return escape(value, {'"': "&quot;"})


def _response(*children: str) -> str:
    return _XML_HEADER + "<Response>" + "".join(children) + "</Response>"


def _say(text: str, voice: str) -> str:
    return f'<Say voice="{_attr(voice)}">{_text(text)}</Say>'


def say_verb(text: str, voice: str) -> str:
    """A ``<Say>`` verb using Twilio's built-in voice."""
    return _say(text, voice)


def play_verb(url: str) -> str:
    """A ``<Play>`` verb for audio hosted at ``url`` (must be publicly reachable by Twilio)."""
    return f"<Play>{_text(url)}</Play>"


def _speak(text: str, voice: str, verb: str | None) -> str:
    """Use a pre-rendered speech verb when a provider supplied one, else Twilio's ``<Say>``."""
    return verb if verb is not None else _say(text, voice)


def _gather(action: str, inner: str) -> str:
    return (
        f'<Gather input="speech" action="{_attr(action)}" method="POST" '
        f'speechTimeout="auto">{inner}</Gather>'
    )


def clip_answer(text: str | None, limit: int = MAX_ANSWER_CHARS) -> str:
    """Make a model answer speakable and at most ``limit`` characters.

    Strips markdown noise and collapses whitespace. When the answer is too long
    it is cut at the last sentence end inside the limit, or at the last word
    boundary if no sentence fits, so the caller never hears a half-word.
    """
    cleaned = _WHITESPACE.sub(" ", _MARKDOWN_NOISE.sub("", text or "")).strip()
    if len(cleaned) <= limit:
        return cleaned
    ends = [m.end() for m in _SENTENCE_END.finditer(cleaned) if m.end() <= limit]
    # Accept a sentence boundary only if it keeps a useful amount of the answer.
    if ends and ends[-1] >= limit // 3:
        return cleaned[: ends[-1]].rstrip()
    window = cleaned[:limit]
    cut = window.rfind(" ")
    return (window[:cut] if cut > 0 else window).rstrip()


def greeting(
    text: str = GREETING_TEXT,
    *,
    action: str,
    voice: str = DEFAULT_VOICE,
    verb: str | None = None,
) -> str:
    """Speak an opening line and listen for the caller's first turn.

    ``verb`` is an optional pre-rendered speech verb (see :mod:`app.services.voice.tts`);
    when given, ``text`` is not spoken again.
    """
    return _response(_gather(action, _speak(text, voice, verb)))


def reply(
    answer: str,
    *,
    action: str,
    voice: str = DEFAULT_VOICE,
    verb: str | None = None,
) -> str:
    """Speak the agent's answer (capped), then listen again."""
    return _response(_gather(action, _speak(clip_answer(answer), voice, verb)))


def reprompt(
    *,
    action: str,
    voice: str = DEFAULT_VOICE,
    text: str = RETRY_TEXT,
    verb: str | None = None,
) -> str:
    """Ask the caller to repeat when no speech was captured."""
    return _response(_gather(action, _speak(text, voice, verb)))


def handoff(*, voice: str = DEFAULT_VOICE, team_number: str | None = None) -> str:
    """Connect the caller to a team number, or explain and hang up if none is set.

    ``team_number`` must already be validated E.164 by the caller.
    """
    if team_number:
        return _response(
            _say(HANDOFF_CONNECT_TEXT, voice),
            f"<Dial>{_text(team_number)}</Dial>",
        )
    return _response(_say(HANDOFF_UNAVAILABLE_TEXT, voice), "<Hangup/>")


def goodbye(text: str = ERROR_TEXT, *, voice: str = DEFAULT_VOICE) -> str:
    """Speak a closing line and end the call."""
    return _response(_say(text, voice), "<Hangup/>")

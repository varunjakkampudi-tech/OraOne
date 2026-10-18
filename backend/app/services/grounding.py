"""Answer-level grounding check for model replies.

A reply is grounded only when every sentence that makes a claim is supported by
the passages that were retrieved for it. The check is lexical and deterministic:
a sentence passes when at least ``threshold`` of its content words appear in the
passages. A sentence with letters but no checkable words fails closed.

This is deliberately strict. A paraphrase that adds a new fact fails, and the
caller then uses the passage text. The check does not prove a claim is true. It
proves that the reply does not introduce content absent from the business's own
knowledge.
"""

from __future__ import annotations

import re
from typing import Iterable

# Words that carry no claim on their own.
_STOPWORDS = frozenset(
    """
    the and for are but not you your yours with this that from have has had was
    were will would can could should may might its it's our ours they them their
    there these those what when where which who whom whose how why into over
    under about also just than then too very any all some such only own same
    so if or nor on in of to by at as be been being do does did done is am
    we us me my mine he she his her hers i'm you're we're they're
    """.split()
)

# Letters and digits, including the combining marks of Indic and Arabic text
# that the plain \w class does not match.
_WORD = re.compile("[\\ẁ-ͯ؀-ۿऀ-ॿ฀-๿぀-ヿ一-鿿]+")
_CITATION = re.compile(r"\[\d+\]")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")


def _stem(word: str) -> str:
    """Fold simple English plurals (plans -> plan) so restatements still match."""
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _content_words(text: str) -> set[str]:
    words = _WORD.findall(text.lower())
    return {_stem(w) for w in words if len(w) > 2 and w not in _STOPWORDS}


def _sentences(text: str) -> list[str]:
    cleaned = _CITATION.sub("", text or "")
    return [s.strip() for s in _SENTENCE_END.split(cleaned) if s and s.strip()]


def unsupported_sentences(
    answer: str, passages: Iterable[str], *, threshold: float = 0.75
) -> list[str]:
    """Sentences in ``answer`` that the passages do not support."""
    corpus = _content_words(" ".join(p or "" for p in passages))
    flagged: list[str] = []
    for sentence in _sentences(answer):
        words = _content_words(sentence)
        if not words:
            # Letters we cannot check fail closed. Punctuation or a bare citation
            # makes no claim and passes.
            if any(ch.isalpha() for ch in sentence):
                flagged.append(sentence)
            continue
        overlap = len(words & corpus) / len(words)
        if overlap < threshold:
            flagged.append(sentence)
    return flagged


def is_grounded(
    answer: str, passages: Iterable[str], *, threshold: float = 0.75
) -> bool:
    return not unsupported_sentences(answer, passages, threshold=threshold)

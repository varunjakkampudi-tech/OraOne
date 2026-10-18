"""Answer-level grounding check for model replies.

A reply is grounded only when every sentence that makes a claim is supported by
the passages that were retrieved for it. The check is deterministic and has
three layers, applied to each claim-bearing sentence:

1. Lexical support: at least ``threshold`` of its content words appear in the
   passages (after simple plural folding).
2. Numeric support: every number in the sentence appears in the passages, so a
   swapped price (499 for 599) is caught.
3. Negation agreement: when the sentence closely matches a passage sentence,
   it must agree on whether it is negated, so "is not refundable" does not pass
   against "is refundable".

A sentence with letters but no checkable words fails closed.

This is not a semantic entailment model. It catches common unsupported and
contradicting claims cheaply. It does not prove a claim is true, and it can
refuse valid paraphrases. Treat it as a floor, not a verified-fact label.
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

# Negation markers, in English and Hindi. Contractions are matched as tokens
# after apostrophes are removed.
_NEGATION = frozenset(
    """
    not no never none nothing neither nor cannot cant wont dont doesnt didnt
    isnt arent wasnt werent hasnt havent shouldnt couldnt wouldnt
    नहीं नही कभी
    """.split()
)

# Letters and digits, including the combining marks of Indic and Arabic text
# that the plain \w class does not match.
# Qualifiers change what a claim means: "inside India" vs "outside India". A
# claim that adds one the closest passage does not have is unsupported.
_QUALIFIERS = frozenset(
    """
    inside outside before after more less only free paid minimum maximum least
    most always never everyone nobody
    """.split()
)

# Units change what a number means: 5 days is not 5 hours, 499 rupees is not 499 dollars.
_UNITS = frozenset(
    """
    rupee rupees rs inr dollar dollars usd euro euros percent day days hour hours
    minute minutes week weeks month months year years kg kilogram kilograms km
    litre litres liter liters
    """.split()
)

_WORD = re.compile("[\\ẁ-ͯ؀-ۿऀ-ॿ฀-๿぀-ヿ一-鿿]+")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_CITATION = re.compile(r"\[\d+\]")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")
_BEST_MATCH_OVERLAP = 0.5


def _stem(word: str) -> str:
    """Fold simple English plurals (plans -> plan) so restatements still match."""
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower().replace("'", ""))


def _content_words(text: str) -> set[str]:
    return {_stem(w) for w in _tokens(text) if len(w) > 2 and w not in _STOPWORDS}


def _numbers(text: str) -> set[str]:
    return {m.replace(",", "") for m in _NUMBER.findall(text)}


def _negated(text: str) -> bool:
    return any(token in _NEGATION for token in _tokens(text))


def _qualifiers(text: str) -> set[str]:
    return {token for token in _tokens(text) if token in _QUALIFIERS or token in _UNITS}


def _sentences(text: str) -> list[str]:
    cleaned = _CITATION.sub("", text or "")
    return [s.strip() for s in _SENTENCE_END.split(cleaned) if s and s.strip()]


def _overlap(words: set[str], corpus: set[str]) -> float:
    return len(words & corpus) / len(words) if words else 0.0


def unsupported_sentences(
    answer: str, passages: Iterable[str], *, threshold: float = 0.75
) -> list[str]:
    """Sentences in ``answer`` that the passages do not support."""
    passage_list = [p or "" for p in passages]
    corpus = _content_words(" ".join(passage_list))
    corpus_numbers = (
        set().union(*(_numbers(p) for p in passage_list)) if passage_list else set()
    )
    passage_sentences = [s for p in passage_list for s in _sentences(p)]

    flagged: list[str] = []
    for sentence in _sentences(answer):
        words = _content_words(sentence)
        if not words:
            # Letters we cannot check fail closed. Punctuation or a bare citation
            # makes no claim and passes.
            if any(ch.isalpha() for ch in sentence):
                flagged.append(sentence)
            continue

        # 1. Lexical support.
        if _overlap(words, corpus) < threshold:
            flagged.append(sentence)
            continue

        # 2. Every number must come from the passages.
        if not _numbers(sentence) <= corpus_numbers:
            flagged.append(sentence)
            continue

        # 3. Negation and qualifiers must agree with the closest passage sentence.
        best = max(
            passage_sentences,
            key=lambda s: _overlap(words, _content_words(s)),
            default=None,
        )
        if (
            best is not None
            and _overlap(words, _content_words(best)) >= _BEST_MATCH_OVERLAP
            and (
                _negated(sentence) != _negated(best)
                or _qualifiers(sentence) - _qualifiers(best)
            )
        ):
            flagged.append(sentence)
    return flagged


def is_grounded(
    answer: str, passages: Iterable[str], *, threshold: float = 0.75
) -> bool:
    return not unsupported_sentences(answer, passages, threshold=threshold)


FALLBACK_PREFIX = (
    "I could not confirm that from the knowledge base. The closest source says:"
)
_FALLBACK_CHARS = 600


def enforce_grounded(answer: str, passages: Iterable[str]) -> tuple[str, bool]:
    """Return ``(answer, changed)``.

    When the reply makes a claim the passages do not support, it is replaced by
    the closest passage text, so no unsupported claim reaches the customer. With
    no passages there is nothing to check against, so the reply is returned
    unchanged and ``changed`` is False.
    """
    usable = [p for p in passages if p and p.strip()]
    if not usable or not unsupported_sentences(answer, usable):
        return answer, False
    return f"{FALLBACK_PREFIX}\n\n{usable[0].strip()[:_FALLBACK_CHARS]}", True

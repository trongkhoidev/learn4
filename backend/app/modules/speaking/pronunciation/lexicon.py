"""Lexicon / G2P seam with pronunciation variants, stress and OOV policy.

- A CMUdict-format lexicon file is loaded from an explicit local path when
  configured (no downloads). Each dictionary entry can carry multiple
  pronunciation variants.
- Words with no dictionary entry fall back to a small rule-based G2P whose
  status is always ``approx_rule_based``; it can position evidence but its
  claims stay candidates and are never validated in isolation.
- Proper nouns and unresolved words get status ``unresolved``: the engine
  abstains from phone claims that need their phones.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.core.config import settings
from .policy import (
    APPROX_G2P_STATUS,
    LEXICON_RESOLVED_STATUS,
    LEXICON_UNRESOLVED_STATUS,
)

logger = logging.getLogger(__name__)


@dataclass
class LexiconResult:
    word: str
    status: str  # resolved | approx_rule_based | unresolved
    variants: list[list[str]] = field(default_factory=list)
    stress_phone_index: Optional[int] = None
    source: str = "none"

    @property
    def phones(self) -> list[str]:
        return self.variants[0] if self.variants else []

    @property
    def usable_for_claims(self) -> bool:
        return bool(self.variants)


# --- Rule-based approximate G2P ------------------------------------------------

_G2P_RULES = [
    ("tion", ["SH", "AH", "N"]), ("sion", ["ZH", "AH", "N"]),
    ("ough", ["AH"]), ("igh", ["AY"]), ("eau", ["OW"]),
    ("ch", ["CH"]), ("sh", ["SH"]), ("th", ["TH"]), ("ph", ["F"]),
    ("wh", ["W"]), ("ck", ["K"]), ("ng", ["NG"]), ("ng,", ["NG"]),
    ("qu", ["K", "W"]), ("ee", ["IY"]), ("ea", ["IY"]), ("oo", ["UW"]),
    ("ai", ["EY"]), ("ay", ["EY"]), ("oa", ["OW"]), ("ow", ["OW"]),
    ("ou", ["AW"]), ("oi", ["OY"]), ("oy", ["OY"]), ("ar", ["AA", "R"]),
    ("er", ["ER"]), ("ir", ["ER"]), ("ur", ["ER"]), ("or", ["AO", "R"]),
]
_VOWEL_MAP = {"a": "AE", "e": "EH", "i": "IH", "o": "AA", "u": "AH", "y": "IY"}
_CONSONANT_MAP = {
    "b": "B", "c": "K", "d": "D", "f": "F", "g": "G", "h": "HH", "j": "JH",
    "k": "K", "l": "L", "m": "M", "n": "N", "p": "P", "q": "K", "r": "R",
    "s": "S", "t": "T", "v": "V", "w": "W", "x": "K", "z": "Z",
}
_FINAL_S_VOICELESS_BEFORE = set("PKFT")


def rule_based_g2p(word: str) -> tuple[list[str], Optional[int]]:
    """Approximate phones for a regular word; status is always approx."""
    text = (word or "").strip().lower()
    phones: list[str] = []
    index = 0
    while index < len(text):
        matched = False
        for pattern, phones_out in _G2P_RULES:
            if text.startswith(pattern, index):
                phones.extend(phones_out)
                index += len(pattern)
                matched = True
                break
        if matched:
            continue
        letter = text[index]
        if letter.isalpha():
            if letter in _VOWEL_MAP:
                phones.append(_VOWEL_MAP[letter])
            elif letter in _CONSONANT_MAP:
                phones.append(_CONSONANT_MAP[letter])
        index += 1
    if phones and text and text[-1] == "s" and len(phones) > 1:
        # Final -s variation: /Z/ after voiced sounds, /S/ after voiceless,
        # or an extra syllable /IH Z/. This stays an approximation.
        previous = phones[-2]
        if text.endswith("es"):
            phones.extend(["IH", "Z"])
        elif previous in _FINAL_S_VOICELESS_BEFORE:
            phones[-1] = "S"
        else:
            phones[-1] = "Z"
    if phones and text and text[-1] == "e" and len(phones) > 1:
        phones.pop()  # silent final e approximation
    return phones, (0 if len(phones) > 1 else None)


def _parse_cmu_line(line: str) -> Optional[tuple[str, int, list[str]]]:
    line = line.strip()
    if not line or line.startswith(";;;"):
        return None
    parts = line.split()
    if len(parts) < 2 or "(" not in parts[0] and len(parts) < 2:
        if len(parts) < 2:
            return None
    head = parts[0].upper()
    variant = 0
    if "(" in head:
        base, suffix = head.split("(", 1)
        try:
            variant = int(suffix.strip("()"))
        except ValueError:
            variant = 0
        head = base
    phones = [p for p in parts[1:] if p]
    return head, variant, phones


def _strip_stress(phone: str) -> tuple[str, bool]:
    return phone.rstrip("012"), phone.endswith("")


class Lexicon:
    """Deterministic lexicon adapter; file path comes from explicit config."""

    def __init__(self, path: Optional[str] = None):
        self.path = path if path is not None else settings.pronunciation_lexicon_path
        self._entries: dict[str, list[list[str]]] = {}
        self._stress_index: dict[str, Optional[int]] = {}
        self.loaded = False
        if self.path and Path(self.path).is_file():
            self._load(Path(self.path))
            self.loaded = True

    def _load(self, path: Path) -> None:
        try:
            raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            logger.warning("lexicon unreadable (%s): %s", path, exc)
            return
        for line in raw:
            parsed = _parse_cmu_line(line)
            if parsed is None:
                continue
            head, variant, phones = parsed
            if not self._stress_or_valid(phones):
                continue
            self._entries.setdefault(head, [])
            while len(self._entries[head]) <= variant:
                self._entries[head].append([])
            self._entries[head][variant] = [p for _, p in (self._split(p) for p in phones)]
            if variant == 0:
                self._stress_index[head] = self._primary_stress_index(phones)

    @staticmethod
    def _stress_or_valid(phones) -> bool:
        return all(phone and phone[0].isalpha() for phone in phones)

    @staticmethod
    def _split(phone: str) -> tuple[str, str]:
        return phone, phone.rstrip("012")

    @staticmethod
    def _primary_stress_index(phones: list[str]) -> Optional[int]:
        for index, phone in enumerate(phones):
            if phone.endswith("1"):
                return index
        return None

    def lookup(self, word: str, *, is_proper_noun: bool = False) -> LexiconResult:
        token = (word or "").strip().strip(".,!?;:\"'()[]").upper()
        if not token:
            return LexiconResult(word, LEXICON_UNRESOLVED_STATUS, source="none")
        if token in self._entries:
            return LexiconResult(
                word,
                LEXICON_RESOLVED_STATUS,
                variants=[v for v in self._entries[token] if v] or [self._entries[token][0]],
                stress_phone_index=self._stress_index.get(token),
                source="lexicon_file",
            )
        if is_proper_noun or not token.isalpha():
            # Names, numbers, unknown tokens: do not guess phones silently.
            return LexiconResult(word, LEXICON_UNRESOLVED_STATUS, source="none")
        phones, stress = rule_based_g2p(token)
        if not phones:
            return LexiconResult(word, LEXICON_UNRESOLVED_STATUS, source="none")
        return LexiconResult(
            word, APPROX_G2P_STATUS, variants=[phones],
            stress_phone_index=stress, source="rule_based_g2p",
        )


_DEFAULT = None


def get_lexicon() -> Lexicon:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Lexicon()
    return _DEFAULT

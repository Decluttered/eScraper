import re
import unicodedata
from collections.abc import Iterable

from app.domain.enums import Condition
from app.domain.normalization import NormalizationCandidate, NormalizationResult

TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:gb|tb|mhz)?")
DEFECT_TERMS = {"defekt", "kaputt", "bastler", "artefakte", "funktionsunfähig"}
UNTESTED_TERMS = {"ungetestet", "ungeprüft", "keine funktionsprüfung"}
EMPTY_BOX_TERMS = {"nur ovp", "nur verpackung", "leerkarton", "nicht enthalten"}
BUNDLE_TERMS = {"bundle", "konvolut", "komplett pc", "gaming pc"}


def normalized_text(value: str) -> str:
    lowered = unicodedata.normalize("NFKC", value).lower()
    lowered = re.sub(r"(\d+)\s*(gb|tb|mhz)\b", r"\1\2", lowered)
    return " ".join(TOKEN_PATTERN.findall(lowered))


def _contains_phrase(raw_lower: str, phrases: set[str]) -> bool:
    return any(phrase in raw_lower for phrase in phrases)


def normalize_listing(
    title: str,
    description: str,
    candidates: Iterable[NormalizationCandidate],
) -> NormalizationResult:
    raw_lower = f"{title} {description}".lower()
    text = normalized_text(raw_lower)
    tokens = frozenset(text.split())
    flags: list[str] = []

    if _contains_phrase(raw_lower, DEFECT_TERMS):
        condition = Condition.DEFECTIVE
        flags.append("DEFECTIVE")
    elif _contains_phrase(raw_lower, UNTESTED_TERMS):
        condition = Condition.UNTESTED
        flags.append("UNTESTED")
    else:
        condition = Condition.USED

    if _contains_phrase(raw_lower, EMPTY_BOX_TERMS):
        flags.append("EMPTY_BOX_RISK")
    if _contains_phrase(raw_lower, BUNDLE_TERMS):
        flags.append("BUNDLE")

    matches = [
        candidate
        for candidate in candidates
        if normalized_text(candidate.alias) in text
        and candidate.required_tokens.issubset(tokens)
        and not candidate.excluded_tokens.intersection(tokens)
    ]
    blocking_text = "DEFECTIVE" in flags or "EMPTY_BOX_RISK" in flags
    if len(matches) == 1:
        return NormalizationResult(
            product_id=matches[0].product_id,
            condition=condition,
            confidence_bps=10000,
            flags=tuple(sorted(flags)),
            review_required=blocking_text,
        )

    flags.append("UNCLEAR_VARIANT")
    return NormalizationResult(
        product_id=None,
        condition=condition,
        confidence_bps=0,
        flags=tuple(sorted(set(flags))),
        review_required=True,
    )

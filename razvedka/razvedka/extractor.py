import logging
import re
from dataclasses import dataclass, field

from .keywords import INTENTION_KEYWORDS, FRANCE_KEYWORDS, TEMPORAL_PATTERNS
from .metrics import entities_extracted_total

logger = logging.getLogger("razvedka.extractor")

# Lazy-loaded singletons
_lingua_detector = None
_spacy_nlp = None

# Regex patterns for entity extraction
IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
DOMAIN_PATTERN = re.compile(
    r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)"
    r"+[a-zA-Z]{2,}\b"
)
CVE_PATTERN = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)

# Compiled temporal patterns
_temporal_compiled = [re.compile(p, re.IGNORECASE) for p in TEMPORAL_PATTERNS]

# Language mapping for lingua -> our keyword keys
_LINGUA_MAP = {
    "RUSSIAN": "russian",
    "ENGLISH": "english",
    "ARABIC": "arabic",
    "FRENCH": "french",
}


def _get_lingua_detector():
    global _lingua_detector
    if _lingua_detector is None:
        from lingua import LanguageDetectorBuilder, Language
        _lingua_detector = (
            LanguageDetectorBuilder
            .from_languages(Language.RUSSIAN, Language.ENGLISH, Language.ARABIC, Language.FRENCH)
            .with_minimum_relative_distance(0.25)
            .build()
        )
        logger.info("Lingua detector loaded")
    return _lingua_detector


def _get_spacy_nlp():
    global _spacy_nlp
    if _spacy_nlp is None:
        import spacy
        _spacy_nlp = spacy.load("xx_ent_wiki_sm")
        logger.info("spaCy model loaded")
    return _spacy_nlp


@dataclass
class ExtractionResult:
    language: str | None = None
    entities_targets: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)
    intention_keywords: list[str] = field(default_factory=list)
    temporality: str | None = None
    score_intention: float = 0.0
    score_france: float = 0.0
    raw_entities: dict = field(default_factory=dict)


def extract_intelligence(text: str) -> ExtractionResult:
    """Full extraction pipeline on a message text."""
    if not text or not text.strip():
        return ExtractionResult()

    result = ExtractionResult()

    # 1. Language detection
    try:
        detector = _get_lingua_detector()
        detected = detector.detect_language_of(text)
        if detected:
            result.language = _LINGUA_MAP.get(detected.name, detected.name.lower())
    except Exception:
        logger.debug("Language detection failed", exc_info=True)

    # 2. Regex entity extraction
    text_lower = text.lower()

    ips = IP_PATTERN.findall(text)
    domains = DOMAIN_PATTERN.findall(text)
    cves = CVE_PATTERN.findall(text)

    if ips:
        result.raw_entities["ips"] = ips
        entities_extracted_total.labels(entity_type="ip").inc(len(ips))
    if domains:
        result.raw_entities["domains"] = domains
        entities_extracted_total.labels(entity_type="domain").inc(len(domains))
        result.entities_targets.extend(domains)
    if cves:
        result.raw_entities["cves"] = cves
        entities_extracted_total.labels(entity_type="cve").inc(len(cves))

    # 3. spaCy NER (limit to 1000 chars)
    try:
        nlp = _get_spacy_nlp()
        doc = nlp(text[:1000])
        spacy_ents = []
        for ent in doc.ents:
            if ent.label_ in ("ORG", "GPE", "LOC"):
                spacy_ents.append({"text": ent.text, "label": ent.label_})
                entities_extracted_total.labels(entity_type=ent.label_.lower()).inc()
                if ent.label_ == "GPE":
                    result.countries.append(ent.text)
                elif ent.label_ == "ORG":
                    result.entities_targets.append(ent.text)
        if spacy_ents:
            result.raw_entities["spacy"] = spacy_ents
    except Exception:
        logger.debug("spaCy NER failed", exc_info=True)

    # 4. Keyword matching (weighted intention score)
    total_score = 0.0
    matched_keywords = []

    for lang_keywords in INTENTION_KEYWORDS.values():
        for _category, word_list in lang_keywords.items():
            for keyword, weight in word_list:
                if keyword.lower() in text_lower:
                    total_score += weight
                    matched_keywords.append(keyword)

    result.score_intention = total_score
    result.intention_keywords = list(set(matched_keywords))

    # 5. France scoring
    france_hits = 0
    for kw in FRANCE_KEYWORDS:
        if kw.lower() in text_lower:
            france_hits += 1

    # Also check spaCy entities for France references
    for ent_info in result.raw_entities.get("spacy", []):
        if ent_info.get("label") == "GPE":
            ent_lower = ent_info["text"].lower()
            for fkw in FRANCE_KEYWORDS:
                if fkw.lower() in ent_lower:
                    france_hits += 2
                    break

    result.score_france = min(france_hits / 3.0, 1.0)

    if result.score_france > 0:
        # Add France to countries if not already there
        if "France" not in result.countries:
            result.countries.append("France")

    # 6. Temporal extraction
    temporal_matches = []
    # Check keyword temporals from intention keywords
    for lang_keywords in INTENTION_KEYWORDS.values():
        time_words = lang_keywords.get("time", [])
        for keyword, _weight in time_words:
            if keyword.lower() in text_lower:
                temporal_matches.append(keyword)

    # Check regex temporal patterns
    for pattern in _temporal_compiled:
        matches = pattern.findall(text)
        temporal_matches.extend(matches)

    if temporal_matches:
        result.temporality = "; ".join(list(dict.fromkeys(temporal_matches))[:5])

    # Deduplicate
    result.entities_targets = list(dict.fromkeys(result.entities_targets))
    result.countries = list(dict.fromkeys(result.countries))

    return result

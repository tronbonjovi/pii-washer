import re

import spacy
import tldextract
import tldextract.tldextract as _tldextract_mod
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider

# Force tldextract to use its bundled snapshot only — no network calls.
# Presidio's EmailRecognizer calls tldextract.extract() which would otherwise
# fetch the Public Suffix List over HTTPS on first use.
_tldextract_mod.TLD_EXTRACTOR = tldextract.TLDExtract(
    suffix_list_urls=(),
    fallback_to_snapshot=True,
)


class PIIDetectionEngine:
    VALID_CATEGORIES = ["NAME", "ADDRESS", "PHONE", "EMAIL", "SSN", "DOB", "CCN", "IP", "URL"]

    ENTITY_MAPPING = {
        "PERSON": "NAME",
        "LOCATION": "ADDRESS",
        "PHONE_NUMBER": "PHONE",
        "EMAIL_ADDRESS": "EMAIL",
        "US_SSN": "SSN",
        "CREDIT_CARD": "CCN",
        "IP_ADDRESS": "IP",
        "DATE_TIME": "DOB",
        "URL": "URL",
        "US_STREET_ADDRESS": "ADDRESS",
        "US_ZIP_CODE": "ADDRESS",
    }

    US_STREET_TYPES = [
        "Street", "St", "Avenue", "Ave", "Boulevard", "Blvd",
        "Drive", "Dr", "Lane", "Ln", "Road", "Rd", "Court", "Ct",
        "Place", "Pl", "Way", "Circle", "Cir", "Terrace", "Ter",
        "Trail", "Trl", "Parkway", "Pkwy", "Highway", "Hwy",
    ]

    US_STATE_ABBREVIATIONS = [
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC",
    ]

    ZIP_CONTEXT_WINDOW = 100  # characters before the detected zip span

    DOB_CONTEXT_KEYWORDS = ["born", "birth", "birthday", "dob", "date of birth", "birth date", "birthdate", "age"]
    DOB_CONTEXT_WINDOW = 50

    PII_URL_PATTERNS = [
        "linkedin.com/in/",
        "facebook.com/",
        "github.com/",
        "twitter.com/",
        "x.com/",
        "instagram.com/",
    ]

    # Build the street type alternation from the constant list
    _street_types_pattern = "|".join(US_STREET_TYPES)

    # Full street address pattern
    US_STREET_ADDRESS_PATTERN = (
        r"\b\d{1,5}\s+"                                    # House number
        r"(?:(?:N|S|E|W|North|South|East|West|NE|NW|SE|SW)\.?\s+)?"  # Optional directional
        r"(?:[A-Z][a-zA-Z]*\.?\s+){1,4}"                  # Street name (1-4 words)
        r"(?:" + _street_types_pattern + r")\.?"           # Street type suffix
        r"\b"
    )

    # Zip code patterns
    ZIP_PLUS_4_PATTERN = r"\b\d{5}-\d{4}\b"  # e.g., 62704-1234
    ZIP_5_PATTERN = r"\b\d{5}\b"  # e.g., 62704

    DEFAULT_CONFIDENCE_THRESHOLD = 0.3

    def __init__(self, model_name: str = "en_core_web_lg") -> None:
        nlp = spacy.load(model_name)
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": model_name}],
        })
        nlp_engine = provider.create_engine()
        self._analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])

        street_recognizer = PatternRecognizer(
            supported_entity="US_STREET_ADDRESS",
            patterns=[Pattern("us_street_address", self.US_STREET_ADDRESS_PATTERN, 0.65)],
            supported_language="en",
        )
        self._analyzer.registry.add_recognizer(street_recognizer)

        zip_recognizer = PatternRecognizer(
            supported_entity="US_ZIP_CODE",
            patterns=[
                Pattern("us_zip_plus_4", self.ZIP_PLUS_4_PATTERN, 0.7),
                Pattern("us_zip_5", self.ZIP_5_PATTERN, 0.4),
            ],
            supported_language="en",
        )
        self._analyzer.registry.add_recognizer(zip_recognizer)

    def detect(self, text: str, confidence_threshold: float = 0.3, language: str = "en") -> list[dict]:
        if not isinstance(text, str) or not text:
            raise ValueError("Text cannot be empty")
        if not (0.0 <= confidence_threshold <= 1.0):
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")

        results = self._analyzer.analyze(
            text=text,
            entities=list(self.ENTITY_MAPPING.keys()),
            language=language,
        )

        detections = []
        for result in results:
            category = self.ENTITY_MAPPING.get(result.entity_type)
            if category is None:
                continue

            start = result.start
            end = result.end
            confidence = result.score
            original_value = text[start:end]

            if category == "DOB" and not self._has_dob_context(text, start):
                continue

            if category == "URL" and not self._is_pii_url(original_value):
                continue

            if category == "ADDRESS" and result.entity_type == "US_ZIP_CODE":
                # ZIP+4 always passes (distinctive format)
                if "-" not in original_value:
                    # 5-digit zip: require address context
                    if not self._has_zip_context(text, start):
                        continue

            if confidence < confidence_threshold:
                continue

            detections.append({
                "category": category,
                "original_value": original_value,
                "positions": [{"start": start, "end": end}],
                "confidence": confidence,
            })

        detections = self._deduplicate(detections)
        detections.sort(key=lambda d: d["positions"][0]["start"])

        for i, det in enumerate(detections, start=1):
            det["id"] = f"pii_{i:03d}"

        return detections

    def get_supported_categories(self) -> list[str]:
        return list(self.VALID_CATEGORIES)

    def get_entity_mapping(self) -> dict:
        return dict(self.ENTITY_MAPPING)

    def _has_dob_context(self, text: str, span_start: int) -> bool:
        window_start = max(0, span_start - self.DOB_CONTEXT_WINDOW)
        context = text[window_start:span_start].lower()
        return any(kw in context for kw in self.DOB_CONTEXT_KEYWORDS)

    def _has_zip_context(self, text: str, span_start: int) -> bool:
        """Check if address-related context appears before a 5-digit zip code."""
        window_start = max(0, span_start - self.ZIP_CONTEXT_WINDOW)
        context = text[window_start:span_start]

        # Check for state abbreviations (case-sensitive — they're uppercase)
        for abbr in self.US_STATE_ABBREVIATIONS:
            # Match as whole word: preceded by space/comma/start, followed by space/comma/end
            if re.search(r"(?:^|[\s,])" + abbr + r"(?:[\s,]|$)", context):
                return True

        # Check for street type suffixes (case-insensitive, whole word)
        for st_type in self.US_STREET_TYPES:
            if re.search(r"\b" + re.escape(st_type) + r"\.?\b", context, re.IGNORECASE):
                return True

        return False

    def _is_pii_url(self, url: str) -> bool:
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in self.PII_URL_PATTERNS)

    def _deduplicate(self, detections: list[dict]) -> list[dict]:
        if len(detections) <= 1:
            return detections

        to_remove = set()
        for i in range(len(detections)):
            if i in to_remove:
                continue
            for j in range(i + 1, len(detections)):
                if j in to_remove:
                    continue

                s_i = detections[i]["positions"][0]["start"]
                e_i = detections[i]["positions"][0]["end"]
                s_j = detections[j]["positions"][0]["start"]
                e_j = detections[j]["positions"][0]["end"]

                if s_i == s_j and e_i == e_j:
                    # Exact span match: keep higher confidence
                    if detections[i]["confidence"] >= detections[j]["confidence"]:
                        to_remove.add(j)
                    else:
                        to_remove.add(i)
                elif s_j >= s_i and e_j <= e_i:
                    # j is contained in i: keep i (longer)
                    to_remove.add(j)
                elif s_i >= s_j and e_i <= e_j:
                    # i is contained in j: keep j (longer)
                    to_remove.add(i)

        return [d for idx, d in enumerate(detections) if idx not in to_remove]

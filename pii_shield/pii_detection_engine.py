import spacy
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider


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
    }

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

    DEFAULT_CONFIDENCE_THRESHOLD = 0.3

    def __init__(self, model_name: str = "en_core_web_lg") -> None:
        nlp = spacy.load(model_name)
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": model_name}],
        })
        nlp_engine = provider.create_engine()
        self._analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])

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

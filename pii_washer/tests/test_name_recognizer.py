import pytest
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from pii_washer.name_recognizer import TitleNameRecognizer, DictionaryNameRecognizer, CapitalizedPairRecognizer


@pytest.fixture(scope="module")
def title_recognizer():
    return TitleNameRecognizer()


@pytest.fixture(scope="module")
def analyzer(title_recognizer):
    """Minimal analyzer with just the title recognizer for isolated testing."""
    provider = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
    })
    engine = provider.create_engine()
    analyzer = AnalyzerEngine(nlp_engine=engine, supported_languages=["en"])
    analyzer.registry.add_recognizer(title_recognizer)
    return analyzer


class TestTitleNameRecognizer:
    def test_mr_lastname(self, analyzer):
        results = analyzer.analyze("Please contact Mr. Smith regarding the matter.", language="en", entities=["PERSON"])
        persons = [r for r in results if r.entity_type == "PERSON"]
        assert any("Smith" in "Please contact Mr. Smith regarding the matter."[r.start:r.end] for r in persons)

    def test_dr_full_name(self, analyzer):
        results = analyzer.analyze("Dr. Jane Doe will see you now.", language="en", entities=["PERSON"])
        persons = [r for r in results if r.entity_type == "PERSON"]
        texts = ["Dr. Jane Doe will see you now."[r.start:r.end] for r in persons]
        assert any("Jane" in t and "Doe" in t for t in texts)

    def test_professor_name(self, analyzer):
        results = analyzer.analyze("Professor Michael Williams teaches physics.", language="en", entities=["PERSON"])
        persons = [r for r in results if r.entity_type == "PERSON"]
        texts = ["Professor Michael Williams teaches physics."[r.start:r.end] for r in persons]
        assert any("Williams" in t for t in texts)

    def test_judge_name(self, analyzer):
        results = analyzer.analyze("The case was heard by Judge Patricia Chen.", language="en", entities=["PERSON"])
        persons = [r for r in results if r.entity_type == "PERSON"]
        texts = ["The case was heard by Judge Patricia Chen."[r.start:r.end] for r in persons]
        assert any("Chen" in t for t in texts)

    def test_title_without_period(self, analyzer):
        results = analyzer.analyze("Mr Smith called yesterday.", language="en", entities=["PERSON"])
        persons = [r for r in results if r.entity_type == "PERSON"]
        assert any("Smith" in "Mr Smith called yesterday."[r.start:r.end] for r in persons)

    def test_three_word_name(self, analyzer):
        results = analyzer.analyze("Mrs. Mary Jane Watson arrived.", language="en", entities=["PERSON"])
        persons = [r for r in results if r.entity_type == "PERSON"]
        texts = ["Mrs. Mary Jane Watson arrived."[r.start:r.end] for r in persons]
        assert any("Watson" in t for t in texts)

    def test_military_title(self, analyzer):
        results = analyzer.analyze("Sgt. Robert Johnson reported for duty.", language="en", entities=["PERSON"])
        persons = [r for r in results if r.entity_type == "PERSON"]
        assert any("Johnson" in "Sgt. Robert Johnson reported for duty."[r.start:r.end] for r in persons)

    def test_confidence_is_0_7(self, title_recognizer):
        """Title recognizer should produce confidence of 0.7."""
        for pattern in title_recognizer.patterns:
            assert pattern.score == 0.7

    def test_no_match_without_title(self, analyzer):
        """Should not produce results for names without titles (that's NER's job)."""
        text = "John Smith went to the store."
        results = analyzer.analyze(text, language="en", entities=["PERSON"])
        title_results = [r for r in results if r.score == 0.7]
        assert len(title_results) == 0


@pytest.fixture(scope="module")
def dict_recognizer():
    return DictionaryNameRecognizer()


class TestDictionaryNameRecognizer:
    def test_common_first_last(self, dict_recognizer):
        text = "Jane Doe submitted the application."
        results = dict_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        assert any("Jane" in text[r.start:r.end] for r in results)

    def test_case_insensitive_lookup(self, dict_recognizer):
        text = "JAMES Wilson was present."
        results = dict_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        assert any("JAMES" in text[r.start:r.end] for r in results)

    def test_first_name_with_two_surnames(self, dict_recognizer):
        text = "Mary Jane Watson was there."
        results = dict_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        assert len(results) >= 1

    def test_no_match_non_name(self, dict_recognizer):
        text = "The table was large and wooden."
        results = dict_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        assert len(results) == 0

    def test_no_match_first_name_alone(self, dict_recognizer):
        """A first name without a capitalized surname should not match."""
        text = "James went to the store."
        results = dict_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        assert len(results) == 0

    def test_confidence_is_0_4(self, dict_recognizer):
        text = "Robert Smith attended the meeting."
        results = dict_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        for r in results:
            assert r.score == 0.4


@pytest.fixture(scope="module")
def cap_recognizer():
    return CapitalizedPairRecognizer()


class TestCapitalizedPairRecognizer:
    def test_mid_sentence_pair(self, cap_recognizer):
        text = "The defendant, Marcus Chen, pleaded not guilty."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        texts = [text[r.start:r.end] for r in results]
        assert any("Marcus" in t and "Chen" in t for t in texts)

    def test_no_match_sentence_start(self, cap_recognizer):
        text = "Big Apple is a nickname for New York."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        texts = [text[r.start:r.end] for r in results]
        assert not any("Big Apple" in t for t in texts)

    def test_no_match_after_period(self, cap_recognizer):
        text = "Done. Good Morning everyone."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        texts = [text[r.start:r.end] for r in results]
        assert not any("Good Morning" in t for t in texts)

    def test_no_match_after_colon(self, cap_recognizer):
        text = "Subject: Big News today."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        texts = [text[r.start:r.end] for r in results]
        assert not any("Big News" in t for t in texts)

    def test_no_match_after_bullet(self, cap_recognizer):
        text = "Items:\n- Red Widget is on sale."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        texts = [text[r.start:r.end] for r in results]
        assert not any("Red Widget" in t for t in texts)

    def test_no_match_month_names(self, cap_recognizer):
        text = "She visited in January February was cold."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        texts = [text[r.start:r.end] for r in results]
        assert not any("January February" in t for t in texts)

    def test_no_match_org_suffix(self, cap_recognizer):
        text = "She works at Acme Corp downtown."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        texts = [text[r.start:r.end] for r in results]
        assert not any("Acme Corp" in t for t in texts)

    def test_no_match_state_name(self, cap_recognizer):
        text = "They drove through New Mexico last summer."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        texts = [text[r.start:r.end] for r in results]
        assert not any("New Mexico" in t for t in texts)

    def test_after_comma_mid_sentence(self, cap_recognizer):
        text = "The award went to the director, Steven Park, for his work."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        texts = [text[r.start:r.end] for r in results]
        assert any("Steven" in t and "Park" in t for t in texts)

    def test_confidence_is_0_3(self, cap_recognizer):
        text = "The director, Marcus Chen, spoke."
        results = cap_recognizer.analyze(text, entities=["PERSON"], nlp_artifacts=None, regex_flags=0)
        for r in results:
            assert r.score == 0.3

"""Tests for writing-standards detectors."""
from __future__ import annotations

from corpus_inference_query.detectors import run_all
from corpus_inference_query.detectors.base import Violation
from corpus_inference_query.detectors.rules import (
    detect_clarity,
    detect_cohesion,
    detect_concision,
    detect_voice_agency,
    detect_diction_register,
    detect_sentence_rhythm,
    detect_audience_fit,
    detect_argument_honesty,
    detect_opening_craft,
    detect_closing_craft,
    detect_concrete_abstract,
    detect_style_consciousness,
)


class TestRegistry:
    def test_run_all_returns_dict_with_violations_and_skipped(self) -> None:
        result = run_all("Hello world.")
        assert "violations" in result
        assert "skipped_rules" in result
        assert isinstance(result["violations"], list)
        assert isinstance(result["skipped_rules"], list)

    def test_run_all_empty_text_no_error(self) -> None:
        result = run_all("")
        assert isinstance(result, dict)

    def test_voice_fidelity_always_in_skipped(self) -> None:
        result = run_all("Any text.")
        skipped_ids = {s["rule_id"] for s in result["skipped_rules"]}
        assert "§13" in skipped_ids

    def test_audience_fit_skipped_when_no_types(self) -> None:
        result = run_all("Some text.", types=None)
        skipped_ids = {s["rule_id"] for s in result["skipped_rules"]}
        assert "§7" in skipped_ids

    def test_type_addendum_not_applied_without_matching_type(self) -> None:
        result = run_all("Short text.", types=["essay"])
        violation_ids = {v["rule_id"] for v in result["violations"]}
        assert "§B" not in violation_ids  # email addendum should not fire

    def test_type_addendum_applied_with_matching_type(self) -> None:
        # With stubs returning [], violations should be empty but no error
        result = run_all("Short text.", types=["email"])
        assert isinstance(result["violations"], list)


class TestClarity:
    def test_long_sentence_flagged(self) -> None:
        long = "The committee which had been formed by the board which was appointed by the shareholders who voted at the meeting held in March decided to defer action pending further review of all available options."
        result = detect_clarity(long)
        assert result is not None
        assert len(result) == 1
        assert result[0].rule_id == "§1"
        assert result[0].severity == "warning"

    def test_short_clear_sentence_clean(self) -> None:
        assert detect_clarity("Sentences make readers.") == []

    def test_nested_relative_clauses_flagged(self) -> None:
        nested = "The report that the analyst who the firm hired last year wrote contained errors that mattered."
        result = detect_clarity(nested)
        assert result is not None and len(result) >= 1

    def test_multiple_sentences_one_long(self) -> None:
        text = "Dogs bark. " + "a " * 45 + "sentence."
        result = detect_clarity(text)
        assert len(result) == 1


class TestCohesion:
    def test_no_overlap_flagged(self) -> None:
        text = "Dogs are loyal. Quantum physics is complex."
        result = detect_cohesion(text)
        assert result is not None and len(result) >= 1

    def test_overlapping_sentences_clean(self) -> None:
        text = "The experiment failed. The failure was first noticed by the team."
        assert detect_cohesion(text) == []

    def test_single_sentence_not_flagged(self) -> None:
        assert detect_cohesion("Hello.") == []


class TestConcision:
    def test_wordy_phrase_flagged(self) -> None:
        text = "Due to the fact that the report was late, we met."
        result = detect_concision(text)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§3"

    def test_multiple_wordy_phrases(self) -> None:
        text = "In the event that we fail, due to the fact that resources are limited, we must act."
        result = detect_concision(text)
        assert len(result) >= 2

    def test_clean_sentence_no_violation(self) -> None:
        assert detect_concision("The report was late because resources were limited.") == []

    def test_very_unique_flagged(self) -> None:
        result = detect_concision("This is a very unique opportunity.")
        assert len(result) >= 1


class TestVoiceAgency:
    def test_high_passive_rate_flagged(self) -> None:
        passive = "The decision was made. The report was reviewed. The findings were approved. The plan was implemented."
        result = detect_voice_agency(passive)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§4"

    def test_active_sentences_clean(self) -> None:
        active = "The committee decided. They reviewed the report. The team approved the findings."
        assert detect_voice_agency(active) == []

    def test_high_nominalization_density_flagged(self) -> None:
        text = "The implementation of the transformation required the commitment of the organization to the achievement of the improvement."
        result = detect_voice_agency(text)
        assert result is not None and len(result) >= 1


class TestDictionRegister:
    def test_casual_in_formal_type_flagged(self) -> None:
        text = "The system is gonna be totally awesome once we fix this."
        result = detect_diction_register(text, types=["technical-doc"])
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§5"

    def test_casual_in_informal_type_clean(self) -> None:
        text = "This is gonna be awesome, I promise!"
        assert detect_diction_register(text, types=["blog-post"]) == []

    def test_no_types_no_violation(self) -> None:
        text = "It's kinda like a function."
        assert detect_diction_register(text, types=None) == []


class TestSentenceRhythm:
    def test_uniform_short_sentences_flagged(self) -> None:
        text = "Dogs bark. Cats meow. Birds fly. Fish swim. Mice run."
        result = detect_sentence_rhythm(text)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§6"

    def test_varied_sentences_clean(self) -> None:
        text = "Dogs bark. The cat sat quietly on the mat, watching the birds outside the window. Mice run."
        assert detect_sentence_rhythm(text) == []

    def test_fewer_than_three_sentences_clean(self) -> None:
        assert detect_sentence_rhythm("Hello. World.") == []


class TestAudienceFit:
    def test_complex_email_flagged(self) -> None:
        long_sent = "The multifaceted ramifications of the aforementioned contractual obligations necessitate immediate remediation of the underlying systemic deficiencies which have been identified."
        result = detect_audience_fit(long_sent, types=["email"])
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§7"

    def test_no_types_returns_none(self) -> None:
        result = detect_audience_fit("Some text.", types=None)
        assert result is None

    def test_unrecognized_type_returns_empty(self) -> None:
        result = detect_audience_fit("Some text.", types=["podcast"])
        assert result == []


class TestArgumentHonesty:
    def test_hedge_cluster_flagged(self) -> None:
        text = "It perhaps seems like the proposal could possibly work, though it arguably might need more thought and may require revision."
        result = detect_argument_honesty(text)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§8"

    def test_bare_intensifier_flagged(self) -> None:
        text = "Obviously this is the best approach. Clearly everyone agrees."
        result = detect_argument_honesty(text)
        assert result is not None and len(result) >= 1

    def test_clean_argument_no_violation(self) -> None:
        text = "The data shows a 15% improvement. Three independent studies confirm this result."
        assert detect_argument_honesty(text) == []


class TestOpeningCraft:
    def test_first_person_opener_flagged(self) -> None:
        text = "I believe this approach is correct. The evidence supports the claim."
        result = detect_opening_craft(text)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§9"
        assert result[0].severity == "warning"

    def test_my_opener_flagged(self) -> None:
        text = "My experience with this framework has been largely positive. Others agree."
        result = detect_opening_craft(text)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§9"

    def test_clean_opening_no_violation(self) -> None:
        text = "The data tells a clear story. Adoption grew 40% last quarter."
        result = detect_opening_craft(text)
        assert result == []

    def test_empty_text_returns_empty(self) -> None:
        assert detect_opening_craft("") == []

    def test_mid_sentence_i_not_flagged(self) -> None:
        # "I" not at the start of the first sentence should not trigger
        text = "When I look at the numbers, the trend is clear. Growth accelerated."
        result = detect_opening_craft(text)
        assert result == []

    def test_relative_opener_flagged(self) -> None:
        text = "Which approach we choose matters greatly."
        result = detect_opening_craft(text)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§9"


class TestClosingCraft:
    def test_etc_closer_flagged(self) -> None:
        text = "The team reviewed the code. They checked formatting, style, logic, etc."
        result = detect_closing_craft(text)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§10"
        assert result[0].severity == "info"

    def test_and_so_on_closer_flagged(self) -> None:
        text = "We support Python, Ruby, Go, and so on."
        result = detect_closing_craft(text)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§10"

    def test_too_short_closer_flagged(self) -> None:
        # Fewer than 4 words in last sentence
        text = "The framework is reliable. Use it."
        result = detect_closing_craft(text)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§10"

    def test_clean_closing_no_violation(self) -> None:
        text = "The experiment succeeded. The results validate our hypothesis and open new directions for research."
        result = detect_closing_craft(text)
        assert result == []

    def test_empty_text_returns_empty(self) -> None:
        assert detect_closing_craft("") == []


class TestConcreteAbstract:
    def test_high_abstract_density_flagged(self) -> None:
        # Many abstract nouns above 15% threshold with >=30 words
        text = (
            "The implementation of the transformation required the commitment of the "
            "organization to the achievement of improvement through the establishment "
            "of governance and the recognition of the importance of collaboration and "
            "communication."
        )
        result = detect_concrete_abstract(text)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§11"
        assert result[0].severity == "warning"

    def test_low_abstract_density_clean(self) -> None:
        text = (
            "The dog ran across the yard. It jumped over the fence and landed in the "
            "grass. The children laughed and chased after it down the street."
        )
        result = detect_concrete_abstract(text)
        assert result == []

    def test_fewer_than_30_words_skipped(self) -> None:
        # Under 30 words should return [] even with abstract terms
        text = "The implementation of transformation through commitment to organization."
        result = detect_concrete_abstract(text)
        assert result == []

    def test_empty_text_returns_empty(self) -> None:
        assert detect_concrete_abstract("") == []


class TestStyleConsciousness:
    def test_consecutive_same_start_flagged(self) -> None:
        text = "The dog barked loudly. The cat hissed back. The bird flew away."
        result = detect_style_consciousness(text)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§12"
        assert result[0].severity == "info"

    def test_varied_sentence_starts_clean(self) -> None:
        text = "The dog barked loudly. A cat hissed back. Then the bird flew away."
        result = detect_style_consciousness(text)
        assert result == []

    def test_single_sentence_returns_empty(self) -> None:
        assert detect_style_consciousness("One sentence here.") == []

    def test_multiple_consecutive_same_starts(self) -> None:
        # Three consecutive sentences starting with "The" — two pairs flagged
        text = "The sun rose early. The moon had just set. The stars were fading fast."
        result = detect_style_consciousness(text)
        assert result is not None and len(result) >= 2
        assert result[0].rule_id == "§12"

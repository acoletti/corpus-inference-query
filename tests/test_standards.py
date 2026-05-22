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
    detect_voice_fidelity,
    detect_transitions,
    detect_lede_and_title,
    detect_article,
    detect_email,
    detect_letter,
    detect_technical_doc,
    detect_newsletter,
    detect_op_ed,
    detect_blog_post,
    detect_white_paper,
    detect_memo,
    detect_speech,
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

    def test_run_all_returns_types_used(self) -> None:
        result = run_all("Some text.", types=["essay"])
        assert "types_used" in result
        assert "essay" in result["types_used"]


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

    def test_and_so_forth_ender_flagged(self) -> None:
        result = detect_closing_craft("These include forms, functions, and so forth.")
        assert result is not None and len(result) >= 1

    def test_among_others_ender_flagged(self) -> None:
        result = detect_closing_craft("We studied Python, Java, and Rust, among others.")
        assert result is not None and len(result) >= 1


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


class TestVoiceFidelity:
    def test_always_returns_none(self) -> None:
        assert detect_voice_fidelity("Any text.") is None

    def test_always_skipped_regardless_of_types(self) -> None:
        assert detect_voice_fidelity("Text.", types=["essay"]) is None

    def test_empty_text_still_none(self) -> None:
        assert detect_voice_fidelity("") is None


class TestTransitions:
    def test_abrupt_shift_flagged(self) -> None:
        text = "Dogs are loyal animals.\n\nQuantum physics describes subatomic particles."
        result = detect_transitions(text)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§14"

    def test_transition_word_suppresses_flag(self) -> None:
        text = "Dogs are loyal animals.\n\nHowever, cats are more independent."
        result = detect_transitions(text)
        assert result == []

    def test_single_paragraph_no_violation(self) -> None:
        assert detect_transitions("Just one paragraph.") == []

    def test_stem_overlap_suppresses_flag(self) -> None:
        # "dog" in both paragraphs — stem overlap should suppress the §14 violation
        text = "The dog barked all morning.\n\nThe dogs were restless and noisy."
        result = detect_transitions(text)
        assert result == []

    def test_three_paragraphs_multiple_gaps_checked(self) -> None:
        # Both gaps are abrupt — should get 2 violations
        text = (
            "Dogs are loyal animals.\n\n"
            "Quantum physics describes subatomic particles.\n\n"
            "The French Revolution began in 1789."
        )
        result = detect_transitions(text)
        assert result is not None and len(result) >= 2


class TestLedeAndTitle:
    def test_long_first_sentence_flagged(self) -> None:
        # Deliberately over the 35-word threshold
        long = (
            "The complex interplay of market forces, regulatory changes, "
            "and shifting consumer preferences in the modern global economy "
            "requires a nuanced understanding of macroeconomic trends, "
            "geopolitical forces, institutional dynamics, and the evolving "
            "policy frameworks that collectively determine outcomes."
        )
        assert len(long.split()) > 35, "test fixture must exceed 35 words"
        result = detect_lede_and_title(long, types=["article"])
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§15"

    def test_question_opener_flagged(self) -> None:
        result = detect_lede_and_title("Have you ever wondered why cats purr?", types=["essay"])
        assert result is not None and len(result) >= 1

    def test_clean_lede_no_violation(self) -> None:
        result = detect_lede_and_title("Silence speaks volumes.", types=["article"])
        assert result == []

    def test_non_applicable_type_skipped(self) -> None:
        result = detect_lede_and_title("Have you ever wondered why?", types=["technical-doc"])
        assert result == []


# ---------------------------------------------------------------------------
# §A  Article
# ---------------------------------------------------------------------------

_LONG_SINGLE_BLOCK = " ".join(["word"] * 210)  # 210 words, no blank lines

_ARTICLE_MULTI_PARA = "\n\n".join([
    "This piece examines how machine learning changes journalism today.",
    "The first implication is speed of production and automated content.",
    "The second implication concerns editorial oversight and fact-checking.",
])

# 160 words, no nut-graf markers (no "this", "here", "today", "in this")
_ARTICLE_NO_NUT_GRAF_LONG = " ".join(["The reporters gathered."] * 5 + ["word"] * 145)


class TestDetectArticle:
    def test_non_article_type_returns_empty(self) -> None:
        result = detect_article(_LONG_SINGLE_BLOCK, types=["email"])
        assert result == []

    def test_none_types_returns_empty(self) -> None:
        result = detect_article(_LONG_SINGLE_BLOCK, types=None)
        assert result == []

    def test_short_single_block_no_structure_violation(self) -> None:
        # Under 200 words → no structure warning even without paragraphs
        short = " ".join(["word"] * 150)
        result = detect_article(short, types=["article"])
        assert result == []

    def test_long_single_block_flags_structure(self) -> None:
        result = detect_article(_LONG_SINGLE_BLOCK, types=["article"])
        rule_ids = [v.rule_id for v in result]
        assert "§A" in rule_ids
        severities = [v.severity for v in result if v.rule_id == "§A"]
        assert "warning" in severities

    def test_multi_paragraph_article_no_structure_violation(self) -> None:
        result = detect_article(_ARTICLE_MULTI_PARA, types=["article"])
        structure_violations = [v for v in result if v.severity == "warning"]
        assert len(structure_violations) == 0

    def test_nut_graf_present_no_info_violation(self) -> None:
        text = (
            "In this article, I will explain how climate change affects coral reefs. "
            "Scientists have documented a 50% decline over the past three decades. "
            "The data comes from surveys conducted in the Pacific and Atlantic oceans.\n\n"
            "Rising water temperatures bleach the coral and disrupt the ecosystem. "
            "Recovery requires years of stable, cooler conditions that are rarely seen."
        )
        result = detect_article(text, types=["article"])
        info_violations = [v for v in result if v.severity == "info"]
        assert len(info_violations) == 0

    def test_no_nut_graf_long_text_flags_info(self) -> None:
        result = detect_article(_ARTICLE_NO_NUT_GRAF_LONG, types=["article"])
        info_violations = [v for v in result if v.severity == "info"]
        assert len(info_violations) >= 1
        assert info_violations[0].rule_id == "§A"

    def test_longform_journalism_type_also_triggers(self) -> None:
        result = detect_article(_LONG_SINGLE_BLOCK, types=["longform-journalism"])
        rule_ids = [v.rule_id for v in result]
        assert "§A" in rule_ids


# ---------------------------------------------------------------------------
# §B  Email
# ---------------------------------------------------------------------------

_SHORT_EMAIL = "Hi there,\n\nPlease review the attached document.\n\nThanks!"

_LONG_EMAIL = (
    "Hello team,\n\n"
    + "This message contains many words. " * 40
    + "\n\nBest regards."
)

_NO_GREETING_EMAIL = "The document has been reviewed and approved. Proceed with the next steps in the workflow."


class TestDetectEmail:
    def test_non_email_type_returns_empty(self) -> None:
        result = detect_email(_LONG_EMAIL, types=["article"])
        assert result == []

    def test_none_types_returns_empty(self) -> None:
        result = detect_email(_LONG_EMAIL, types=None)
        assert result == []

    def test_short_email_with_greeting_no_violations(self) -> None:
        result = detect_email(_SHORT_EMAIL, types=["email"])
        assert result == []

    def test_long_email_flagged(self) -> None:
        result = detect_email(_LONG_EMAIL, types=["email"])
        rule_ids = [v.rule_id for v in result]
        assert "§B" in rule_ids
        long_violations = [v for v in result if "long" in v.snippet.lower() or v.rule_id == "§B"]
        assert len(long_violations) >= 1

    def test_email_without_greeting_flagged(self) -> None:
        result = detect_email(_NO_GREETING_EMAIL, types=["email"])
        rule_ids = [v.rule_id for v in result]
        assert "§B" in rule_ids

    def test_all_violations_are_info_severity(self) -> None:
        result = detect_email(_LONG_EMAIL, types=["email"])
        for v in result:
            assert v.severity == "info"

    def test_email_with_sincerely_no_greeting_violation(self) -> None:
        text = "Sincerely, " + "word " * 20
        result = detect_email(text, types=["email"])
        greeting_violations = [v for v in result if "greeting" in v.snippet.lower()]
        assert len(greeting_violations) == 0


# ---------------------------------------------------------------------------
# §C  Letter
# ---------------------------------------------------------------------------

_SHORT_LETTER = "Hi."

_LONG_LETTER_WITH_CLOSINGS = (
    "Dear Mr. Smith,\n\n"
    "I am writing to express my interest in the position advertised on your website. "
    "My background in software engineering spans over ten years and includes "
    "substantial experience with distributed systems and cloud infrastructure. "
    "I have led teams of engineers across three continents and delivered "
    "mission-critical services to millions of users. I believe my skills and "
    "experience would make a strong contribution to your organisation.\n\n"
    "Sincerely,\nJane Doe"
)

_LETTER_NO_SALUTATION = (
    "The position requires five years of relevant experience. "
    "Candidates must demonstrate proficiency in Python and cloud technologies. "
    "Applications close on the first of next month."
)


class TestDetectLetter:
    def test_non_letter_type_returns_empty(self) -> None:
        result = detect_letter(_LONG_LETTER_WITH_CLOSINGS, types=["email"])
        assert result == []

    def test_none_types_returns_empty(self) -> None:
        result = detect_letter(_LONG_LETTER_WITH_CLOSINGS, types=None)
        assert result == []

    def test_well_formed_letter_no_violations(self) -> None:
        result = detect_letter(_LONG_LETTER_WITH_CLOSINGS, types=["letter"])
        assert result == []

    def test_short_letter_flagged(self) -> None:
        result = detect_letter(_SHORT_LETTER, types=["letter"])
        rule_ids = [v.rule_id for v in result]
        assert "§C" in rule_ids

    def test_letter_without_salutation_flagged(self) -> None:
        result = detect_letter(_LETTER_NO_SALUTATION, types=["letter"])
        rule_ids = [v.rule_id for v in result]
        assert "§C" in rule_ids

    def test_cover_letter_type_triggers(self) -> None:
        result = detect_letter(_SHORT_LETTER, types=["cover-letter"])
        rule_ids = [v.rule_id for v in result]
        assert "§C" in rule_ids

    def test_all_violations_are_info_severity(self) -> None:
        result = detect_letter(_LETTER_NO_SALUTATION, types=["letter"])
        for v in result:
            assert v.severity == "info"


# ---------------------------------------------------------------------------
# §D  Technical Doc
# ---------------------------------------------------------------------------

_PLAIN_PROSE_NO_MARKDOWN = (
    "The system processes requests asynchronously. "
    "Workers poll a shared queue and execute tasks in order. "
    "Results are written back to the database after each task completes. "
    "Clients poll for completion status using the job identifier. "
    "Timeouts are enforced by a watchdog process that runs every sixty seconds."
)

_MARKDOWN_DOC = (
    "## Overview\n\n"
    "The system **must** handle 1000 requests per second.\n\n"
    "```python\nretry(n=3)\n```\n\n"
    "- Workers poll a shared queue.\n"
    "- Results are written back to the database."
)

_LONG_PROSE_NO_MODALS = " ".join(
    ["The system processes requests and workers execute tasks and results get stored."] * 18
)


class TestDetectTechnicalDoc:
    def test_non_technical_type_returns_empty(self) -> None:
        result = detect_technical_doc(_PLAIN_PROSE_NO_MARKDOWN, types=["email"])
        assert result == []

    def test_none_types_returns_empty(self) -> None:
        result = detect_technical_doc(_PLAIN_PROSE_NO_MARKDOWN, types=None)
        assert result == []

    def test_well_formed_markdown_doc_no_structure_violation(self) -> None:
        result = detect_technical_doc(_MARKDOWN_DOC, types=["technical-doc"])
        structure_violations = [v for v in result if v.severity == "warning"]
        assert len(structure_violations) == 0

    def test_plain_prose_no_markdown_flags_warning(self) -> None:
        result = detect_technical_doc(_PLAIN_PROSE_NO_MARKDOWN, types=["technical-doc"])
        rule_ids = [v.rule_id for v in result]
        assert "§D" in rule_ids
        warning_violations = [v for v in result if v.severity == "warning"]
        assert len(warning_violations) >= 1

    def test_readme_type_triggers(self) -> None:
        result = detect_technical_doc(_PLAIN_PROSE_NO_MARKDOWN, types=["readme"])
        rule_ids = [v.rule_id for v in result]
        assert "§D" in rule_ids

    def test_rfc_type_triggers(self) -> None:
        result = detect_technical_doc(_PLAIN_PROSE_NO_MARKDOWN, types=["rfc"])
        rule_ids = [v.rule_id for v in result]
        assert "§D" in rule_ids

    def test_long_doc_no_modals_flags_info(self) -> None:
        result = detect_technical_doc(_LONG_PROSE_NO_MODALS, types=["technical-doc"])
        info_violations = [v for v in result if v.severity == "info"]
        assert len(info_violations) >= 1
        assert info_violations[0].rule_id == "§D"

    def test_doc_with_must_no_modal_info_violation(self) -> None:
        text = "## Setup\n\nYou must install dependencies first. " + "word " * 200
        result = detect_technical_doc(text, types=["technical-doc"])
        info_violations = [v for v in result if v.severity == "info"]
        assert len(info_violations) == 0


# ---------------------------------------------------------------------------
# §E  Newsletter
# ---------------------------------------------------------------------------

_LONG_NEWSLETTER = "word " * 410
_SHORT_NEWSLETTER = "word " * 40
_GOOD_NEWSLETTER = "word " * 300


class TestDetectNewsletter:
    def test_non_newsletter_type_returns_empty(self) -> None:
        result = detect_newsletter(_LONG_NEWSLETTER, types=["email"])
        assert result == []

    def test_none_types_returns_empty(self) -> None:
        result = detect_newsletter(_LONG_NEWSLETTER, types=None)
        assert result == []

    def test_good_length_newsletter_no_violations(self) -> None:
        result = detect_newsletter(_GOOD_NEWSLETTER, types=["newsletter"])
        assert result == []

    def test_long_newsletter_flagged(self) -> None:
        result = detect_newsletter(_LONG_NEWSLETTER, types=["newsletter"])
        rule_ids = [v.rule_id for v in result]
        assert "§E" in rule_ids

    def test_short_newsletter_flagged(self) -> None:
        result = detect_newsletter(_SHORT_NEWSLETTER, types=["newsletter"])
        rule_ids = [v.rule_id for v in result]
        assert "§E" in rule_ids

    def test_all_violations_are_info_severity(self) -> None:
        result = detect_newsletter(_LONG_NEWSLETTER, types=["newsletter"])
        for v in result:
            assert v.severity == "info"

    def test_exactly_400_words_not_flagged(self) -> None:
        text = "word " * 400
        result = detect_newsletter(text, types=["newsletter"])
        assert result == []

    def test_exactly_50_words_not_flagged(self) -> None:
        text = "word " * 50
        result = detect_newsletter(text, types=["newsletter"])
        assert result == []


# ---------------------------------------------------------------------------
# §F  Op-Ed
# ---------------------------------------------------------------------------

_OP_ED_PERSONAL = (
    "I believe the city council has made a grave mistake. "
    "My experience living in this neighbourhood for twenty years gives me standing to say "
    "that the proposed development will destroy the character we have built together. "
    "When I attended the public meeting last Tuesday, I heard many residents share the same concern. "
    "We must push back before it is too late to change course. "
    "The council members have ignored community input at every stage of this process. "
    "I urge every resident to contact their representative today. "
    "Our voices matter and we deserve to be heard in these discussions. "
    "The decision affects thousands of families and should not be taken lightly. "
    "Let us stand together and demand accountability from those we elected to serve us."
)  # >300 words? No — let's check: ~120 words. Good for first-person test, not word-count test.

_OP_ED_NO_FIRST_PERSON = (
    "The city council has made a grave mistake. "
    "The proposed development will destroy the neighbourhood character. "
    "Residents have been ignored at every stage. "
    "The decision affects thousands of families and should not be taken lightly. "
    "Accountability must be demanded from elected officials."
)

_OP_ED_LONG_PERSONAL = (
    "I believe the city council has made a grave mistake. " * 60
)  # ~660 words with first person


class TestDetectOpEd:
    def test_non_op_ed_type_returns_empty(self) -> None:
        result = detect_op_ed(_OP_ED_NO_FIRST_PERSON, types=["article"])
        assert result == []

    def test_none_types_returns_empty(self) -> None:
        result = detect_op_ed(_OP_ED_NO_FIRST_PERSON, types=None)
        assert result == []

    def test_no_first_person_flagged(self) -> None:
        result = detect_op_ed(_OP_ED_NO_FIRST_PERSON, types=["op-ed"])
        rule_ids = [v.rule_id for v in result]
        assert "§F" in rule_ids
        voice_violations = [v for v in result if "personal voice" in v.snippet.lower() or "first person" in v.snippet.lower() or v.rule_id == "§F"]
        assert len(voice_violations) >= 1

    def test_first_person_present_no_voice_violation(self) -> None:
        # Personal voice present — should NOT flag voice violation
        result = detect_op_ed(_OP_ED_PERSONAL, types=["op-ed"])
        voice_violations = [v for v in result if "personal voice" in (v.rule_id + "")]
        # Just check no rule about personal voice fires (check message content)
        snippets = [v.snippet for v in result]
        assert not any("personal voice" in s for s in snippets)

    def test_short_op_ed_flagged(self) -> None:
        # Under 300 words — should flag word count
        result = detect_op_ed(_OP_ED_NO_FIRST_PERSON, types=["op-ed"])
        rule_ids = [v.rule_id for v in result]
        assert "§F" in rule_ids

    def test_long_personal_op_ed_no_violations(self) -> None:
        result = detect_op_ed(_OP_ED_LONG_PERSONAL, types=["op-ed"])
        assert result == []

    def test_all_violations_are_info_severity(self) -> None:
        result = detect_op_ed(_OP_ED_NO_FIRST_PERSON, types=["op-ed"])
        for v in result:
            assert v.severity == "info"

    def test_my_triggers_first_person_detection(self) -> None:
        text = "My view on the matter is clear. " * 60  # >300 words
        result = detect_op_ed(text, types=["op-ed"])
        voice_violations = [v for v in result if "personal voice" in v.snippet]
        assert len(voice_violations) == 0  # "my" is present → no voice violation


# ---------------------------------------------------------------------------
# §G  Blog Post
# ---------------------------------------------------------------------------

_SINGLE_BLOCK_BLOG_LONG = "word " * 160  # >150 words, single paragraph

_MULTI_PARA_BLOG = "\n\n".join([
    "This is the first paragraph about the topic at hand.",
    "This is the second paragraph that continues the discussion.",
    "This is the third paragraph with concluding thoughts.",
])

_LONG_BLOG = "This is a typical blog sentence. " * 100  # >800 words

_REGULAR_BLOG_LONG = "This is a typical blog sentence. " * 100  # tests "regular-blog" alias


class TestDetectBlogPost:
    def test_non_blog_type_returns_empty(self) -> None:
        result = detect_blog_post(_SINGLE_BLOCK_BLOG_LONG, types=["article"])
        assert result == []

    def test_none_types_returns_empty(self) -> None:
        result = detect_blog_post(_SINGLE_BLOCK_BLOG_LONG, types=None)
        assert result == []

    def test_single_paragraph_long_text_flagged(self) -> None:
        result = detect_blog_post(_SINGLE_BLOCK_BLOG_LONG, types=["blog-post"])
        rule_ids = [v.rule_id for v in result]
        assert "§G" in rule_ids

    def test_multi_paragraph_no_structure_violation(self) -> None:
        result = detect_blog_post(_MULTI_PARA_BLOG, types=["blog-post"])
        structure_violations = [v for v in result if "paragraph" in v.snippet.lower()]
        assert len(structure_violations) == 0

    def test_long_blog_flagged(self) -> None:
        result = detect_blog_post(_LONG_BLOG, types=["blog-post"])
        rule_ids = [v.rule_id for v in result]
        assert "§G" in rule_ids

    def test_regular_blog_alias_triggers(self) -> None:
        result = detect_blog_post(_LONG_BLOG, types=["regular-blog"])
        rule_ids = [v.rule_id for v in result]
        assert "§G" in rule_ids

    def test_all_violations_are_info_severity(self) -> None:
        result = detect_blog_post(_SINGLE_BLOCK_BLOG_LONG, types=["blog-post"])
        for v in result:
            assert v.severity == "info"

    def test_short_single_para_no_structure_violation(self) -> None:
        # ≤150 words single paragraph should NOT flag paragraph break issue
        text = "word " * 100
        result = detect_blog_post(text, types=["blog-post"])
        structure_violations = [v for v in result if "paragraph" in v.snippet.lower()]
        assert len(structure_violations) == 0


# ---------------------------------------------------------------------------
# §H  White Paper
# ---------------------------------------------------------------------------

_SHORT_WHITE_PAPER = "word " * 800  # <1000 words, no headers

_LONG_WHITE_PAPER_NO_HEADERS = "word " * 1200  # >1000 words, no headers

_LONG_WHITE_PAPER_WITH_HEADERS = (
    "# Introduction\n\n"
    + "word " * 400
    + "\n\n## Analysis\n\n"
    + "word " * 400
    + "\n\n### Conclusion\n\n"
    + "word " * 400
)


class TestDetectWhitePaper:
    def test_non_white_paper_type_returns_empty(self) -> None:
        result = detect_white_paper(_SHORT_WHITE_PAPER, types=["article"])
        assert result == []

    def test_none_types_returns_empty(self) -> None:
        result = detect_white_paper(_SHORT_WHITE_PAPER, types=None)
        assert result == []

    def test_short_white_paper_flags_warning(self) -> None:
        result = detect_white_paper(_SHORT_WHITE_PAPER, types=["white-paper"])
        severities = [v.severity for v in result]
        assert "warning" in severities
        rule_ids = [v.rule_id for v in result]
        assert "§H" in rule_ids

    def test_short_white_paper_also_flags_no_headers(self) -> None:
        result = detect_white_paper(_SHORT_WHITE_PAPER, types=["white-paper"])
        info_violations = [v for v in result if v.severity == "info"]
        assert len(info_violations) >= 1

    def test_long_white_paper_no_headers_flags_info(self) -> None:
        result = detect_white_paper(_LONG_WHITE_PAPER_NO_HEADERS, types=["white-paper"])
        info_violations = [v for v in result if v.severity == "info"]
        assert len(info_violations) >= 1
        rule_ids = [v.rule_id for v in result]
        assert "§H" in rule_ids

    def test_long_white_paper_with_headers_no_violations(self) -> None:
        result = detect_white_paper(_LONG_WHITE_PAPER_WITH_HEADERS, types=["white-paper"])
        assert result == []

    def test_length_violation_is_warning_severity(self) -> None:
        result = detect_white_paper(_SHORT_WHITE_PAPER, types=["white-paper"])
        warning_violations = [v for v in result if v.severity == "warning"]
        assert len(warning_violations) >= 1


# ---------------------------------------------------------------------------
# §I  Memo
# ---------------------------------------------------------------------------

_WELL_FORMED_MEMO = (
    "To: All Staff\nFrom: Jane Doe\nDate: 2024-01-15\nSubject: Q1 Goals\n\n"
    "Please review the attached goals document before the team meeting on Friday."
)

_LONG_MEMO = (
    "To: All Staff\nFrom: Jane Doe\nDate: 2024-01-15\nSubject: Q1 Goals\n\n"
    + "This memo covers important topics in detail. " * 60
)

_MEMO_NO_HEADERS = (
    "Please review the attached goals document before the team meeting on Friday. "
    "The meeting will cover our progress against targets."
)


class TestDetectMemo:
    def test_non_memo_type_returns_empty(self) -> None:
        result = detect_memo(_LONG_MEMO, types=["email"])
        assert result == []

    def test_none_types_returns_empty(self) -> None:
        result = detect_memo(_LONG_MEMO, types=None)
        assert result == []

    def test_well_formed_short_memo_no_violations(self) -> None:
        result = detect_memo(_WELL_FORMED_MEMO, types=["memo"])
        assert result == []

    def test_long_memo_flagged(self) -> None:
        result = detect_memo(_LONG_MEMO, types=["memo"])
        rule_ids = [v.rule_id for v in result]
        assert "§I" in rule_ids

    def test_memo_without_header_fields_flagged(self) -> None:
        result = detect_memo(_MEMO_NO_HEADERS, types=["memo"])
        rule_ids = [v.rule_id for v in result]
        assert "§I" in rule_ids

    def test_all_violations_are_info_severity(self) -> None:
        result = detect_memo(_LONG_MEMO, types=["memo"])
        for v in result:
            assert v.severity == "info"

    def test_re_header_field_recognized(self) -> None:
        text = "Re: Budget Review\n\nPlease confirm your attendance."
        result = detect_memo(text, types=["memo"])
        header_violations = [v for v in result if "header" in v.snippet.lower()]
        assert len(header_violations) == 0


# ---------------------------------------------------------------------------
# §J  Speech
# ---------------------------------------------------------------------------

_SPEECH_WITH_ADDRESS = (
    "My fellow colleagues, tonight we gather to celebrate an important milestone. "
    "You have worked tirelessly this year, and your efforts have paid off. "
    "We are stronger together, and our progress shows what we can do. "
    "Thank you all for being here today to mark this achievement."
)

_SPEECH_NO_ADDRESS = (
    "The committee reviewed the annual budget. "
    "Expenditures increased by twelve percent. "
    "Revenue projections remain on target. "
    "The board approved the proposed allocations."
)

_SPEECH_LONG_SENTENCES = (
    "The organization has decided after extensive deliberation and exhaustive consultation "
    "with multiple stakeholders across all departments, regional offices, and executive "
    "committees that the proposed restructuring plan will be implemented beginning next quarter. "
    "The committee has also determined after thoroughly reviewing the detailed financial "
    "projections prepared by the external consultants that substantial additional capital "
    "investment will be required before the second phase of the initiative can begin properly."
)

_TALK_TRANSCRIPT_WITH_ADDRESS = (
    "Welcome everyone to this year's conference. "
    "Today we will explore how our industry is changing. "
    "Your questions and feedback are vital to our progress. "
    "We look forward to a productive discussion with you all."
)


class TestDetectSpeech:
    def test_non_speech_type_returns_empty(self) -> None:
        result = detect_speech(_SPEECH_NO_ADDRESS, types=["article"])
        assert result == []

    def test_none_types_returns_empty(self) -> None:
        result = detect_speech(_SPEECH_NO_ADDRESS, types=None)
        assert result == []

    def test_speech_with_address_no_address_violation(self) -> None:
        result = detect_speech(_SPEECH_WITH_ADDRESS, types=["speech"])
        address_violations = [v for v in result if "direct address" in v.snippet]
        assert len(address_violations) == 0

    def test_speech_without_address_flagged(self) -> None:
        result = detect_speech(_SPEECH_NO_ADDRESS, types=["speech"])
        rule_ids = [v.rule_id for v in result]
        assert "§J" in rule_ids

    def test_long_sentences_in_speech_flagged(self) -> None:
        result = detect_speech(_SPEECH_LONG_SENTENCES, types=["speech"])
        rule_ids = [v.rule_id for v in result]
        assert "§J" in rule_ids

    def test_talk_transcript_alias_triggers(self) -> None:
        result = detect_speech(_SPEECH_NO_ADDRESS, types=["talk-transcript"])
        rule_ids = [v.rule_id for v in result]
        assert "§J" in rule_ids

    def test_all_violations_are_info_severity(self) -> None:
        result = detect_speech(_SPEECH_NO_ADDRESS, types=["speech"])
        for v in result:
            assert v.severity == "info"

    def test_talk_transcript_with_address_no_address_violation(self) -> None:
        result = detect_speech(_TALK_TRANSCRIPT_WITH_ADDRESS, types=["talk-transcript"])
        address_violations = [v for v in result if "direct address" in v.snippet]
        assert len(address_violations) == 0

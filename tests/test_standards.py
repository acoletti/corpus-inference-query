"""Fixture-based tests for individual writing-standards detectors.

Each detector is exercised directly with (text, repo, types) so tests stay
independent of registry wiring; CorpusRepository.check_against_standards
integration is covered separately.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from corpus_inference_query.corpus_repository import CorpusRepository
from corpus_inference_query.detectors import rules
from corpus_inference_query.detectors.registry import infer_types
from corpus_inference_query.detectors.types import RuleViolation, SkippedRule

_FIXTURE_CORPUS = Path(__file__).parent / "fixtures" / "corpus"


@pytest.fixture()
def repo() -> CorpusRepository:
    return CorpusRepository(_FIXTURE_CORPUS)


class TestS1Clarity:
    def test_long_sentence_flagged(self, repo: CorpusRepository) -> None:
        text = (
            "This is an extraordinarily long sentence that keeps going and going "
            "and going, adding clause after clause after clause, without ever "
            "pausing to let the reader catch a breath or understand what is being "
            "said, which makes it very hard to follow along at all in one pass."
        )
        result = rules.check_s1_clarity(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§1"

    def test_short_clear_sentence_passes(self, repo: CorpusRepository) -> None:
        result = rules.check_s1_clarity("The cat sat on the mat.", repo, [])
        assert result is None


class TestS2Cohesion:
    def test_disconnected_sentences_flagged(self, repo: CorpusRepository) -> None:
        text = (
            "Dogs bark loudly outside.\n\n"
            "Mountains rise near the coast. Bicycles need oil regularly. "
            "Coffee tastes bitter today. Rockets launch from the desert."
        )
        result = rules.check_s2_cohesion(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§2"

    def test_connected_sentences_pass(self, repo: CorpusRepository) -> None:
        text = (
            "The dog ran across the yard. The dog barked at the mailman. "
            "The mailman waved at the dog."
        )
        result = rules.check_s2_cohesion(text, repo, [])
        assert result is None


class TestS3Concision:
    def test_redundant_phrase_flagged(self, repo: CorpusRepository) -> None:
        text = "Each and every one of us must act."
        result = rules.check_s3_concision(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§3"
        assert "each and every" in result.snippet.lower()

    def test_concise_text_passes(self, repo: CorpusRepository) -> None:
        result = rules.check_s3_concision("We must act now.", repo, [])
        assert result is None


class TestS4Voice:
    def test_high_passive_rate_flagged(self, repo: CorpusRepository) -> None:
        text = (
            "The ball was thrown by John. The window was broken by the storm. "
            "The cake was baked by Maria."
        )
        result = rules.check_s4_voice(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§4"

    def test_active_voice_passes(self, repo: CorpusRepository) -> None:
        text = "John threw the ball. The storm broke the window. Maria baked the cake."
        result = rules.check_s4_voice(text, repo, [])
        assert result is None


class TestS5Diction:
    def test_unglossed_acronym_flagged(self, repo: CorpusRepository) -> None:
        text = "We measured latency using the RPC framework across the fleet."
        result = rules.check_s5_diction(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§5"
        assert result.snippet == "RPC"

    def test_glossed_acronym_passes(self, repo: CorpusRepository) -> None:
        text = "We measured latency using RPC (remote procedure call) across the fleet."
        result = rules.check_s5_diction(text, repo, [])
        assert result is None


class TestS6Rhythm:
    def test_monotonous_lengths_flagged(self, repo: CorpusRepository) -> None:
        text = (
            "The cat sat down. The dog ran fast. The bird flew high. "
            "The fish swam deep. The frog hopped far."
        )
        result = rules.check_s6_rhythm(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§6"

    def test_erratic_lengths_flagged(self, repo: CorpusRepository) -> None:
        text = (
            "Go. No. Stop. Wait. This incredibly long sentence goes on and on and on "
            "describing many many different things one after another without any pause "
            "whatsoever continuing well beyond what would normally be considered "
            "reasonable for a single sentence in ordinary everyday prose writing today."
        )
        result = rules.check_s6_rhythm(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§6"

    def test_typical_variation_passes(self, repo: CorpusRepository) -> None:
        text = (
            "The cat sat down. Later that afternoon the dog ran across the yard. "
            "The bird flew high above trees. Meanwhile the fish swam deep beneath "
            "the surface of the pond. The frog hopped far across the muddy field."
        )
        result = rules.check_s6_rhythm(text, repo, [])
        assert result is None

    def test_short_text_skipped_not_flagged(self, repo: CorpusRepository) -> None:
        result = rules.check_s6_rhythm("Short text. Two sentences.", repo, [])
        assert result is None


class TestS7AudienceFit:
    def test_grade_outside_band_flagged(self, repo: CorpusRepository) -> None:
        text = (
            "The multidimensional ramifications of institutionalized organizational "
            "bureaucratization necessitate comprehensive reconceptualization of "
            "interdepartmental communication methodologies within contemporary "
            "administrative frameworks."
        )
        result = rules.check_s7_audience_fit(text, repo, ["email"])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§7"

    def test_grade_within_band_passes(self, repo: CorpusRepository) -> None:
        text = (
            "Please review the attached report before our meeting tomorrow afternoon. "
            "Let me know if you have any questions about the budget numbers we "
            "discussed last week."
        )
        result = rules.check_s7_audience_fit(text, repo, ["email"])
        assert result is None

    def test_unknown_type_skipped(self, repo: CorpusRepository) -> None:
        result = rules.check_s7_audience_fit("Some text.", repo, [])
        assert isinstance(result, SkippedRule)
        assert result.rule_id == "§7"
        assert result.reason_code == "type_unknown"


class TestS8ArgumentHonesty:
    def test_hedge_cluster_flagged(self, repo: CorpusRepository) -> None:
        text = (
            "Perhaps this is true. Arguably it could be argued that some might say "
            "the results were positive."
        )
        result = rules.check_s8_argument_honesty(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§8"

    def test_unsupported_intensifiers_flagged(self, repo: CorpusRepository) -> None:
        text = (
            "Clearly this is obviously correct, and it is undeniably the best "
            "approach available today for everyone."
        )
        result = rules.check_s8_argument_honesty(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§8"

    def test_measured_claims_pass(self, repo: CorpusRepository) -> None:
        text = (
            "The results suggest a modest improvement in performance across most "
            "test cases we examined."
        )
        result = rules.check_s8_argument_honesty(text, repo, [])
        assert result is None


class TestS9Opening:
    def test_long_opening_flagged(self, repo: CorpusRepository) -> None:
        text = (
            "This opening sentence goes on for far too long before it ever arrives "
            "at a point, burying the reader in clause after clause after clause "
            "until any sense of momentum or hook has been thoroughly lost. "
            "The rest of the piece is short."
        )
        result = rules.check_s9_opening(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§9"

    def test_short_opening_passes(self, repo: CorpusRepository) -> None:
        result = rules.check_s9_opening("The war began at dawn. Nobody expected it.", repo, [])
        assert result is None


class TestS10Closing:
    def test_missing_terminal_punctuation_flagged(self, repo: CorpusRepository) -> None:
        text = "This is the opening. This piece just trails off without ending properly"
        result = rules.check_s10_closing(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§10"

    def test_too_short_closing_flagged(self, repo: CorpusRepository) -> None:
        text = "This is the opening sentence of the piece. The end."
        result = rules.check_s10_closing(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§10"

    def test_solid_closing_passes(self, repo: CorpusRepository) -> None:
        text = "This is the opening sentence of the piece. It resolves the thread cleanly."
        result = rules.check_s10_closing(text, repo, [])
        assert result is None


class TestS11Concrete:
    def test_high_abstract_density_flagged(self, repo: CorpusRepository) -> None:
        text = (
            "The organization needs implementation of the specification, "
            "consideration of accountability, and effectiveness within the institution."
        )
        result = rules.check_s11_concrete(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§11"

    def test_concrete_text_passes(self, repo: CorpusRepository) -> None:
        text = "The dog ran across the yard and jumped over the gate quickly."
        result = rules.check_s11_concrete(text, repo, [])
        assert result is None


class TestS12StyleConsciousness:
    def test_large_swing_flagged(self, repo: CorpusRepository) -> None:
        text = (
            "The cat sat. The dog ran. The bird flew.\n\n"
            "This extraordinarily long and elaborately constructed sentence continues "
            "on and on describing many different interconnected things one after "
            "another without any pause whatsoever for a very long time indeed."
        )
        result = rules.check_s12_style_consciousness(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§12"

    def test_consistent_style_passes(self, repo: CorpusRepository) -> None:
        text = (
            "The cat sat down calmly. The dog ran across the yard.\n\n"
            "The bird flew high above the trees. The fish swam through the pond."
        )
        result = rules.check_s12_style_consciousness(text, repo, [])
        assert result is None

    def test_single_paragraph_skipped(self, repo: CorpusRepository) -> None:
        result = rules.check_s12_style_consciousness("Just one paragraph here.", repo, [])
        assert result is None


class _FakeRepo:
    """Minimal CorpusRepository double for exercising §13's skip/score branches."""

    def __init__(self, has_personal: bool, score: float | None) -> None:
        self._has_personal = has_personal
        self._score = score

    def has_corpus_sections(self, corpus: str) -> bool:
        return self._has_personal

    def voice_similarity_score(self, text: str, corpus: str = "personal") -> float | None:
        return self._score

    def find_exemplar_section(self, style=None, type_filter=None, corpus=None):
        return None


class TestS13VoiceFidelity:
    def test_empty_personal_corpus_skipped(self, repo: CorpusRepository) -> None:
        result = rules.check_s13_voice_fidelity("Some text.", repo, [])
        assert isinstance(result, SkippedRule)
        assert result.rule_id == "§13"
        assert result.reason_code == "personal_corpus_empty"

    def test_vector_backend_unavailable_skipped(self) -> None:
        fake = _FakeRepo(has_personal=True, score=None)
        result = rules.check_s13_voice_fidelity("Some text.", fake, [])
        assert isinstance(result, SkippedRule)
        assert result.reason_code == "vector_backend_unavailable"

    def test_low_similarity_flagged(self) -> None:
        fake = _FakeRepo(has_personal=True, score=0.1)
        result = rules.check_s13_voice_fidelity("Some text.", fake, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§13"

    def test_high_similarity_passes(self) -> None:
        fake = _FakeRepo(has_personal=True, score=0.8)
        result = rules.check_s13_voice_fidelity("Some text.", fake, [])
        assert result is None


class TestS14Transitions:
    def test_missing_transition_flagged(self, repo: CorpusRepository) -> None:
        text = (
            "This is the opening paragraph.\n\n"
            "The budget increased last quarter. The team hired three new engineers."
        )
        result = rules.check_s14_transitions(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§14"

    def test_present_transition_passes(self, repo: CorpusRepository) -> None:
        text = (
            "This is the opening paragraph.\n\n"
            "The budget increased last quarter. However, the team hired three new engineers."
        )
        result = rules.check_s14_transitions(text, repo, [])
        assert result is None


class TestS15Lede:
    def test_short_first_paragraph_flagged(self, repo: CorpusRepository) -> None:
        text = "Just one sentence lede.\n\nMore body text follows in later paragraphs."
        result = rules.check_s15_lede(text, repo, ["article"])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§15"

    def test_well_sized_first_paragraph_passes(self, repo: CorpusRepository) -> None:
        text = (
            "This is the first sentence of the lede. It adds necessary context here.\n\n"
            "More body text follows in later paragraphs of the article."
        )
        result = rules.check_s15_lede(text, repo, ["article"])
        assert result is None

    def test_non_article_type_skipped(self, repo: CorpusRepository) -> None:
        result = rules.check_s15_lede("Just one sentence lede.", repo, ["email"])
        assert isinstance(result, SkippedRule)
        assert result.reason_code == "type_unknown"


class TestAArticle:
    def test_short_lede_flagged(self, repo: CorpusRepository) -> None:
        result = rules.check_a_article("Short lede.", repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§A"

    def test_well_sized_lede_passes(self, repo: CorpusRepository) -> None:
        text = (
            "This week the city council approved a new transit plan that will add "
            "three bus routes and extend service hours across downtown neighborhoods "
            "starting next spring."
        )
        result = rules.check_a_article(text, repo, [])
        assert result is None


class TestBEmail:
    def test_no_question_or_request_flagged(self, repo: CorpusRepository) -> None:
        text = "This is just an update with no questions or requests in it at all."
        result = rules.check_b_email(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§B"

    def test_question_mark_passes(self, repo: CorpusRepository) -> None:
        text = "Could you review this by Friday? Thanks in advance."
        result = rules.check_b_email(text, repo, [])
        assert result is None

    def test_request_marker_passes(self, repo: CorpusRepository) -> None:
        text = "Please review the attached file. Let me know your thoughts."
        result = rules.check_b_email(text, repo, [])
        assert result is None


class TestCLetter:
    def test_missing_salutation_flagged(self, repo: CorpusRepository) -> None:
        text = "This letter begins abruptly without any greeting at all."
        result = rules.check_c_letter(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§C"

    def test_salutation_present_passes(self, repo: CorpusRepository) -> None:
        text = "Dear Sam,\n\nThanks for your help last week."
        result = rules.check_c_letter(text, repo, [])
        assert result is None


class TestDTechnicalDoc:
    def test_no_headings_flagged(self, repo: CorpusRepository) -> None:
        text = "This is plain prose with no headings or numbered sections anywhere."
        result = rules.check_d_technical_doc(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§D"

    def test_two_headings_pass(self, repo: CorpusRepository) -> None:
        text = "# Introduction\nSome context.\n\n## Details\nMore content here."
        result = rules.check_d_technical_doc(text, repo, [])
        assert result is None

    def test_two_numbered_sections_pass(self, repo: CorpusRepository) -> None:
        text = "1. First step\nDo this.\n\n2. Second step\nThen this."
        result = rules.check_d_technical_doc(text, repo, [])
        assert result is None


class TestENewsletter:
    def test_no_links_flagged(self, repo: CorpusRepository) -> None:
        text = "This newsletter has no links at all in the body copy."
        result = rules.check_e_newsletter(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§E"

    def test_link_present_passes(self, repo: CorpusRepository) -> None:
        text = "Read more about it [in this article](https://example.com/post)."
        result = rules.check_e_newsletter(text, repo, [])
        assert result is None


class TestInferTypes:
    def test_memo_headers_inferred(self) -> None:
        text = "TO: Team\nFROM: Manager\nRE: Budget\n\nPlease review the attached numbers."
        assert "memo" in infer_types(text)

    def test_subject_line_inferred_as_email(self) -> None:
        text = "Subject: Quarterly update\n\nHi team, please see the attached report."
        assert "email" in infer_types(text)

    def test_salutation_and_signoff_inferred_as_letter(self) -> None:
        text = "Dear Sam,\n\nThanks for your help last week.\n\nSincerely,\nAlex"
        assert "letter" in infer_types(text)

    def test_markdown_headings_inferred_as_blog(self) -> None:
        text = "# My Post\n\nSome intro text.\n\n## Section\nMore text."
        assert "blog" in infer_types(text)

    def test_plain_prose_infers_nothing(self) -> None:
        text = "This is just a plain paragraph with no structural markers at all."
        assert infer_types(text) == []


class TestFOped:
    def test_over_word_limit_flagged(self, repo: CorpusRepository) -> None:
        text = ("word " * 1300).strip() + "."
        result = rules.check_f_oped(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§F"

    def test_under_word_limit_passes(self, repo: CorpusRepository) -> None:
        text = "This is a short op-ed with only a handful of words in total for testing."
        result = rules.check_f_oped(text, repo, [])
        assert result is None


class TestGBlogPost:
    def test_sparse_headings_flagged(self, repo: CorpusRepository) -> None:
        text = "This post has no headings at all. " + ("word " * 700)
        result = rules.check_g_blog_post(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§G"

    def test_frequent_headings_pass(self, repo: CorpusRepository) -> None:
        text = "# Heading One\n" + ("word " * 350) + "\n\n## Heading Two\n" + ("word " * 350)
        result = rules.check_g_blog_post(text, repo, [])
        assert result is None


class TestHWhitePaper:
    def test_long_doc_without_summary_flagged(self, repo: CorpusRepository) -> None:
        text = (
            "This white paper has no relevant keyword in its opening paragraph at all. "
            + ("word " * 1500)
        )
        result = rules.check_h_white_paper(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§H"

    def test_long_doc_with_summary_passes(self, repo: CorpusRepository) -> None:
        text = "Executive Summary: this document covers the key findings. " + ("word " * 1500)
        result = rules.check_h_white_paper(text, repo, [])
        assert result is None

    def test_short_doc_skipped(self, repo: CorpusRepository) -> None:
        result = rules.check_h_white_paper("A short document with no summary.", repo, [])
        assert result is None


class TestIMemo:
    def test_missing_headers_flagged(self, repo: CorpusRepository) -> None:
        text = "This memo just starts talking without any header block at all."
        result = rules.check_i_memo(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§I"

    def test_to_from_headers_pass(self, repo: CorpusRepository) -> None:
        text = "TO: Team\nFROM: Manager\nRE: Budget\n\nPlease review the attached numbers."
        result = rules.check_i_memo(text, repo, [])
        assert result is None


class TestJSpeech:
    def test_long_median_sentence_flagged(self, repo: CorpusRepository) -> None:
        text = (
            "This is an extraordinarily long and elaborately constructed sentence "
            "meant to run on and on for quite some time. "
        ) * 3
        result = rules.check_j_speech(text, repo, [])
        assert isinstance(result, RuleViolation)
        assert result.rule_id == "§J"

    def test_short_punchy_sentences_pass(self, repo: CorpusRepository) -> None:
        text = "We win. We fight. We rise. We stand together now."
        result = rules.check_j_speech(text, repo, [])
        assert result is None


class TestCheckAgainstStandardsIntegration:
    """End-to-end: CorpusRepository.check_against_standards() through the real registry."""

    def test_multi_violation_text_surfaces_multiple_rules(self, repo: CorpusRepository) -> None:
        text = (
            "Each and every one of us must consider the past history of this "
            "endeavor, which was started by the team that inherited it, which "
            "frustrated everyone, which nobody expected."
        )
        result = repo.check_against_standards(text)
        rule_ids = {v.rule_id for v in result.violations}
        assert "§1" in rule_ids
        assert "§3" in rule_ids
        assert all(v.severity in ("warning", "info") for v in result.violations)

    def test_email_type_runs_addendum_and_audience_fit(self, repo: CorpusRepository) -> None:
        text = "This is just an update with no questions or requests in it at all."
        result = repo.check_against_standards(text, types=["email"])
        rule_ids = {v.rule_id for v in result.violations}
        assert "§B" in rule_ids

    def test_no_type_skips_type_dependent_rules(self, repo: CorpusRepository) -> None:
        result = repo.check_against_standards("A short, plain sentence.")
        skip_ids = {s.rule_id for s in result.skipped_rules}
        assert "§7" in skip_ids
        assert "§15" in skip_ids
        assert all(s.reason_code == "type_unknown" for s in result.skipped_rules if s.rule_id in {"§7", "§15"})

    def test_clean_text_no_violations(self, repo: CorpusRepository) -> None:
        text = "The cat sat down calmly. The dog ran across the yard."
        result = repo.check_against_standards(text, types=["email"])
        assert isinstance(result.violations, list)
        assert isinstance(result.skipped_rules, list)

"""Unit tests for the MCP tools in server.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# Patch corpus path before importing so the module doesn't fail at import time
# when the real corpus directory is absent in CI / fresh checkouts.
import os
os.environ.setdefault(
    "CORPUS_INFERENCE_PATH",
    os.path.join(os.path.dirname(__file__), "fixtures", "corpus"),
)

# Reset _repo so the fixture path set above is picked up even if other tests
# have already imported and initialised it.
import corpus_inference_query.server as _srv_mod
_srv_mod._repo = None

from corpus_inference_query.server import (
    _CHARS_PER_TOKEN,
    _MAX_TOKENS_CEILING,
    _TOP_K_CEILING,
    _get_repo,
    check_against_standards,
    find_exemplars,
    find_similar_voice,
    list_corpora,
    lookup_citation,
    query,
    reload,
    suggest_opening,
    suggest_rewrite,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_section(citation="CC §1", content="some content"):
    from corpus_inference_query.indexer import Section
    shorthand = citation.split(" §")[0] if " §" in citation else "CC"
    return Section(
        corpus_id="test",
        shorthand=shorthand,
        chapter="Ch1",
        section_name="Test Section",
        citation=citation,
        content=content,
        line_start=0,
        keywords={"test"},
    )


def _make_mock_repo(**overrides):
    """Return a MagicMock that mimics CorpusRepository's public API."""
    mock = MagicMock()
    mock.search.return_value = "search result"
    mock.list_corpora.return_value = []
    mock.lookup_citation.return_value = "citation result"
    mock.find_exemplars.return_value = "exemplars result"
    mock.check_against_standards.return_value = {
        "status": "not_yet_implemented",
        "text_length": 9,
        "types_provided": [],
        "skipped_rules": ["all"],
    }
    mock.find_similar_voice.return_value = "voice result"
    mock.suggest_opening.return_value = "opening result"
    mock.suggest_rewrite.return_value = "rewrite result"
    from corpus_inference_query.corpus_repository import ReloadResult
    mock.reload.return_value = ReloadResult(status="ok", corpora_count=2, doc_count=5)
    for k, v in overrides.items():
        setattr(mock, k, v)
    return mock


# ---------------------------------------------------------------------------
# Fixture-based integration tests (real corpus on disk)
# ---------------------------------------------------------------------------

class TestIntegration:
    """Smoke tests that exercise all 9 tools against the fixture corpus."""

    def setup_method(self):
        # Reset repo so each test gets a fresh instance from the fixture path.
        import corpus_inference_query.server as srv
        srv._repo = None

    def test_list_corpora_returns_table_with_shorthand_header(self):
        result = list_corpora()
        assert isinstance(result, str)
        assert "Shorthand" in result

    def test_query_citation_returns_string(self):
        result = query("HTWS §")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_query_nl_returns_string(self):
        result = query("subordinating style")
        assert isinstance(result, str)

    def test_query_nl_with_style_filter_returns_string(self):
        result = query("subordinating style", style=["subordinating"])
        assert isinstance(result, str)

    def test_lookup_citation_returns_string(self):
        result = lookup_citation("HTWS §Subordinating")
        assert isinstance(result, str)

    def test_find_exemplars_with_style_returns_string(self):
        result = find_exemplars(style=["subordinating"])
        assert isinstance(result, str)

    def test_check_against_standards_contains_not_yet_implemented(self):
        result = check_against_standards("Some text")
        assert isinstance(result, str)
        assert "not yet implemented" in result

    def test_find_similar_voice_returns_string(self):
        result = find_similar_voice("Some text", corpus="HTWS")
        assert isinstance(result, str)

    def test_suggest_opening_returns_string(self):
        result = suggest_opening("essay")
        assert isinstance(result, str)

    def test_suggest_rewrite_returns_string(self):
        result = suggest_rewrite("short text", target_style="subordinating")
        assert isinstance(result, str)

    def test_reload_returns_reloaded(self):
        result = reload()
        assert isinstance(result, str)
        assert "Reloaded" in result


# ---------------------------------------------------------------------------
# max_tokens clamping (via mocked repo)
# ---------------------------------------------------------------------------

class TestMaxTokensClamp:
    """query() must clamp max_tokens to [1, _MAX_TOKENS_CEILING] before use."""

    def _captured_max_chars(self, max_tokens_input):
        """Return the max_chars value passed to repo.search() for a given max_tokens."""
        captured = {}
        mock_repo = _make_mock_repo()
        mock_repo.search.side_effect = lambda *a, **kw: captured.update(kw) or ""
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            query("some query", max_tokens=max_tokens_input)
        return captured.get("max_chars")

    def test_clamp_zero(self):
        assert self._captured_max_chars(0) == 1 * _CHARS_PER_TOKEN

    def test_clamp_negative(self):
        assert self._captured_max_chars(-100) == 1 * _CHARS_PER_TOKEN

    def test_clamp_above_ceiling(self):
        assert self._captured_max_chars(99999) == _MAX_TOKENS_CEILING * _CHARS_PER_TOKEN

    def test_clamp_at_ceiling(self):
        assert self._captured_max_chars(_MAX_TOKENS_CEILING) == _MAX_TOKENS_CEILING * _CHARS_PER_TOKEN

    def test_clamp_at_one(self):
        assert self._captured_max_chars(1) == 1 * _CHARS_PER_TOKEN

    def test_typical_value_passes_through(self):
        assert self._captured_max_chars(1500) == 1500 * _CHARS_PER_TOKEN


# ---------------------------------------------------------------------------
# top_k clamping
# ---------------------------------------------------------------------------

class TestTopKClamp:
    """query() must clamp top_k to [1, _TOP_K_CEILING]."""

    def _captured_top_k(self, top_k_input):
        captured = {}
        mock_repo = _make_mock_repo()
        mock_repo.search.side_effect = lambda *a, **kw: captured.update(kw) or ""
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            query("some query", top_k=top_k_input)
        return captured.get("top_k")

    def test_clamp_zero(self):
        assert self._captured_top_k(0) == 1

    def test_clamp_negative(self):
        assert self._captured_top_k(-5) == 1

    def test_clamp_above_ceiling(self):
        assert self._captured_top_k(999) == _TOP_K_CEILING

    def test_clamp_at_ceiling(self):
        assert self._captured_top_k(_TOP_K_CEILING) == _TOP_K_CEILING

    def test_typical_value_passes_through(self):
        assert self._captured_top_k(5) == 5


# ---------------------------------------------------------------------------
# query() delegates to repo.search()
# ---------------------------------------------------------------------------

class TestQueryDelegation:
    """query() must pass all parameters through to repo.search()."""

    def test_query_passes_style_filter(self):
        captured = {}
        mock_repo = _make_mock_repo()
        mock_repo.search.side_effect = lambda *a, **kw: captured.update(kw) or ""
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            query("test", style=["subordinating"])
        assert captured.get("style") == ["subordinating"]

    def test_query_passes_type_filter(self):
        captured = {}
        mock_repo = _make_mock_repo()
        mock_repo.search.side_effect = lambda *a, **kw: captured.update(kw) or ""
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            query("test", type_filter=["essay"])
        assert captured.get("type_filter") == ["essay"]

    def test_query_passes_corpus_filter(self):
        captured = {}
        mock_repo = _make_mock_repo()
        mock_repo.search.side_effect = lambda *a, **kw: captured.update(kw) or ""
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            query("test", corpus="HTWS")
        assert captured.get("corpus") == "HTWS"

    def test_query_returns_repo_result(self):
        mock_repo = _make_mock_repo()
        mock_repo.search.return_value = "expected output"
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            result = query("test")
        assert result == "expected output"


# ---------------------------------------------------------------------------
# lookup_citation
# ---------------------------------------------------------------------------

class TestLookupCitation:
    def test_passes_citation_and_max_chars(self):
        captured = {}
        mock_repo = _make_mock_repo()
        mock_repo.lookup_citation.side_effect = lambda *a, **kw: captured.update({"args": a, "kw": kw}) or ""
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            lookup_citation("HTWS §Subordinating", max_tokens=500)
        assert captured["args"][0] == "HTWS §Subordinating"
        assert captured["kw"]["max_chars"] == 500 * _CHARS_PER_TOKEN

    def test_max_tokens_clamped_above_ceiling(self):
        captured = {}
        mock_repo = _make_mock_repo()
        mock_repo.lookup_citation.side_effect = lambda *a, **kw: captured.update(kw) or ""
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            lookup_citation("HTWS §Subordinating", max_tokens=99999)
        assert captured["max_chars"] == _MAX_TOKENS_CEILING * _CHARS_PER_TOKEN


# ---------------------------------------------------------------------------
# find_exemplars
# ---------------------------------------------------------------------------

class TestFindExemplars:
    def test_passes_style_and_type_filter(self):
        captured = {}
        mock_repo = _make_mock_repo()
        mock_repo.find_exemplars.side_effect = lambda **kw: captured.update(kw) or ""
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            find_exemplars(style=["subordinating"], type_filter=["essay"], length="short")
        assert captured["style"] == ["subordinating"]
        assert captured["type_filter"] == ["essay"]
        assert captured["length"] == "short"

    def test_top_k_clamped(self):
        captured = {}
        mock_repo = _make_mock_repo()
        mock_repo.find_exemplars.side_effect = lambda **kw: captured.update(kw) or ""
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            find_exemplars(top_k=999)
        assert captured["top_k"] == _TOP_K_CEILING


# ---------------------------------------------------------------------------
# check_against_standards
# ---------------------------------------------------------------------------

class TestCheckAgainstStandards:
    def test_returns_not_yet_implemented_message(self):
        mock_repo = _make_mock_repo()
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            result = check_against_standards("Some text")
        assert "not yet implemented" in result

    def test_passes_text_and_types(self):
        captured = {}
        mock_repo = _make_mock_repo()
        mock_repo.check_against_standards.side_effect = (
            lambda text, types=None: captured.update({"text": text, "types": types})
            or {"status": "not_yet_implemented", "text_length": 0, "types_provided": [], "skipped_rules": []}
        )
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            check_against_standards("hello", types=["essay"])
        assert captured["text"] == "hello"
        assert captured["types"] == ["essay"]


# ---------------------------------------------------------------------------
# find_similar_voice
# ---------------------------------------------------------------------------

class TestFindSimilarVoice:
    def test_passes_corpus_and_top_k(self):
        captured = {}
        mock_repo = _make_mock_repo()
        mock_repo.find_similar_voice.side_effect = lambda *a, **kw: captured.update({"args": a, "kw": kw}) or ""
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            find_similar_voice("text", corpus="HTWS", top_k=3)
        assert captured["kw"]["corpus"] == "HTWS"
        assert captured["kw"]["top_k"] == 3

    def test_top_k_clamped(self):
        captured = {}
        mock_repo = _make_mock_repo()
        mock_repo.find_similar_voice.side_effect = lambda *a, **kw: captured.update(kw) or ""
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            find_similar_voice("text", top_k=999)
        assert captured["top_k"] == _TOP_K_CEILING


# ---------------------------------------------------------------------------
# suggest_opening
# ---------------------------------------------------------------------------

class TestSuggestOpening:
    def test_passes_type_name_style_topic(self):
        captured = {}
        mock_repo = _make_mock_repo()
        mock_repo.suggest_opening.side_effect = lambda *a, **kw: captured.update({"args": a, "kw": kw}) or ""
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            suggest_opening("essay", style=["subordinating"], topic="writing")
        assert captured["args"][0] == "essay"
        assert captured["kw"]["style"] == ["subordinating"]
        assert captured["kw"]["topic"] == "writing"

    def test_top_k_clamped(self):
        captured = {}
        mock_repo = _make_mock_repo()
        mock_repo.suggest_opening.side_effect = lambda *a, **kw: captured.update(kw) or ""
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            suggest_opening("essay", top_k=999)
        assert captured["top_k"] == _TOP_K_CEILING


# ---------------------------------------------------------------------------
# suggest_rewrite
# ---------------------------------------------------------------------------

class TestSuggestRewrite:
    def test_passes_text_and_target_style(self):
        captured = {}
        mock_repo = _make_mock_repo()
        mock_repo.suggest_rewrite.side_effect = lambda *a, **kw: captured.update({"args": a, "kw": kw}) or ""
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            suggest_rewrite("short text", "subordinating", top_k=3)
        assert captured["args"][0] == "short text"
        assert captured["args"][1] == "subordinating"
        assert captured["kw"]["top_k"] == 3

    def test_top_k_clamped(self):
        captured = {}
        mock_repo = _make_mock_repo()
        mock_repo.suggest_rewrite.side_effect = lambda *a, **kw: captured.update(kw) or ""
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            suggest_rewrite("text", "subordinating", top_k=999)
        assert captured["top_k"] == _TOP_K_CEILING


# ---------------------------------------------------------------------------
# reload tool
# ---------------------------------------------------------------------------

class TestReload:
    """reload() must reset _repo and return a message containing 'Reloaded'."""

    def setup_method(self):
        import corpus_inference_query.server as srv
        srv._repo = None

    def test_reload_resets_repo_and_returns_reloaded(self):
        result = reload()
        assert "Reloaded" in result

    def test_reload_result_contains_section_count(self):
        result = reload()
        # The fixture corpus has sections; count should appear in the message
        assert any(ch.isdigit() for ch in result)

    def test_reload_resets_repo_global(self):
        import corpus_inference_query.server as srv
        # Ensure _repo is set before calling reload
        _ = _get_repo()
        assert srv._repo is not None
        reload()
        # reload() sets _repo = None then immediately rebuilds it via _get_repo()
        # so after the call _repo is a fresh instance (not None)
        assert srv._repo is not None


# ---------------------------------------------------------------------------
# list_corpora — table format
# ---------------------------------------------------------------------------

class TestListCorpora:
    """list_corpora() must return a markdown table with Shorthand header."""

    def test_output_contains_shorthand_header(self):
        result = list_corpora()
        assert "Shorthand" in result

    def test_output_is_markdown_table(self):
        result = list_corpora()
        assert "|" in result

    def test_output_contains_corpus_names(self):
        result = list_corpora()
        # Fixture corpus has HTWS and Strunk
        assert "HTWS" in result
        assert "Strunk" in result

    def test_empty_corpora_returns_no_corpora_message(self):
        mock_repo = _make_mock_repo()
        mock_repo.list_corpora.return_value = []
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            result = list_corpora()
        assert "No corpora" in result


# ---------------------------------------------------------------------------
# Startup warmup
# ---------------------------------------------------------------------------

class TestStartupWarmup:
    """main() must attempt to warm up the vector store before mcp.run()."""

    def test_warmup_called_before_mcp_run(self):
        call_order = []
        mock_repo = _make_mock_repo()
        mock_repo._get_vector_store.side_effect = lambda: call_order.append("warmup")
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            with patch(
                "corpus_inference_query.server.mcp.run",
                side_effect=lambda **kw: call_order.append("run"),
            ):
                from corpus_inference_query.server import main
                main()
        assert call_order == ["warmup", "run"]

    def test_warmup_failure_does_not_prevent_server_start(self):
        """A corpus-missing error at warmup must be swallowed so mcp.run() still fires."""
        ran = []
        mock_repo = _make_mock_repo()
        mock_repo._get_vector_store.side_effect = RuntimeError("corpus missing")
        with patch("corpus_inference_query.server._get_repo", return_value=mock_repo):
            with patch(
                "corpus_inference_query.server.mcp.run",
                side_effect=lambda **kw: ran.append(True),
            ):
                from corpus_inference_query.server import main
                main()
        assert ran == [True]


# ---------------------------------------------------------------------------
# NL score threshold (search.py) — unchanged
# ---------------------------------------------------------------------------

class TestNLScoreThreshold:
    """_search_natural_language must filter out low-confidence matches."""

    def _run_nl_search(self, sections, query_str, top_k=5):
        from corpus_inference_query.search import _search_natural_language
        return _search_natural_language(sections, query_str, max_chars=4000, top_k=top_k)

    def _make_matching_section(self, name="generators"):
        from corpus_inference_query.indexer import Section
        return Section(
            corpus_id="test",
            shorthand="CC",
            chapter="Ch1",
            section_name=name,
            citation=f"CC §{name}",
            content=f"Content about {name} in depth.",
            line_start=0,
            keywords={name, "generators", "yield"},
        )

    def _make_unrelated_section(self):
        from corpus_inference_query.indexer import Section
        return Section(
            corpus_id="test",
            shorthand="CC",
            chapter="Ch2",
            section_name="Unrelated Topic",
            citation="CC §Unrelated",
            content="Completely unrelated content about databases.",
            line_start=0,
            keywords={"database", "sql", "schema"},
        )

    def test_high_scoring_section_is_returned(self):
        sections = [self._make_matching_section("generators")]
        result = self._run_nl_search(sections, "generators yield delegation")
        assert "generators" in result.lower()

    def test_low_scoring_section_is_filtered(self):
        sections = [self._make_unrelated_section()]
        result = self._run_nl_search(sections, "generators yield delegation")
        assert "No relevant sections found" in result

    def test_threshold_filters_weak_from_mixed_set(self):
        good = self._make_matching_section("generators")
        bad = self._make_unrelated_section()
        result = self._run_nl_search([good, bad], "generators yield delegation")
        assert "generators" in result.lower()
        assert "Unrelated" not in result

# M1: Rename + Scaffold — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the copied `code-inference-query` codebase into `corpus-inference-query` — package, env vars, console entry, and module/data-class shape — while keeping the test suite green. Establish a fixture writing-corpus so M2 has something to query against.

**Architecture:** Refactor-only. No new tools, no `corpus.toml` loader yet (that arrives in M2). Replace the hardcoded `CORPUS_SPECS` list (which currently names code corpora) with hardcoded writing-corpus stubs that include the new two-axis tags. All Section/CorpusSpec instances gain `style_tags: list[str]` and `type_tags: list[str]` defaulting to empty lists. Tests are updated to use the new shorthand names (HTWS, Strunk) and new field shapes.

**Tech Stack:** Python 3.11+, `mcp>=1.0,<2.0`, hatchling build backend, ruff + mypy, pytest. Optional `[vector]` extras: lancedb + fastembed.

**Spec reference:** `docs/superpowers/specs/2026-05-22-corpus-inference-query-design.md`, especially §3.2 (rename plan), §3.4 (two-axis tagging), §8.1 (repo layout), §9 (M1 scope).

**Out of scope for M1 (in later milestones):** `corpus.toml` loader (M2), MCP tool surface beyond rename (M2), standards detectors (M3), Gutenberg seeding (M4), editorial-review integration (M5), `/writing` skill (M6), CI + GitHub repo (M7).

---

## File Structure

### Files to create

| Path | Responsibility |
|---|---|
| `.git/` | Initialize git repo for this directory |
| `tests/fixtures/corpus/corpus.toml` | Placeholder writing-corpus manifest (read by M2; M1 leaves it as a marker file) |
| `tests/fixtures/corpus/references/fish-howtowriteasentence/ch01.md` | Stub HTWS content for fixture queries |
| `tests/fixtures/corpus/references/strunk-elements-of-style/omit-needless-words.md` | Stub Strunk content for fixture queries |

### Files to modify

| Path | Change |
|---|---|
| `src/code_inference_query/` → `src/corpus_inference_query/` | Rename package directory |
| `src/corpus_inference_query/__init__.py` | Rewrite (currently empty/1-line) |
| `src/corpus_inference_query/corpus_config.py` | Add `style_tags`/`type_tags` to `CorpusSpec`; replace `CORPUS_SPECS` with writing-corpus stubs (HTWS, Strunk) |
| `src/corpus_inference_query/indexer.py` | Add `style_tags`/`type_tags` to `Section`; update internal imports |
| `src/corpus_inference_query/server.py` | Rename env vars, MCP server name, internal imports |
| `src/corpus_inference_query/search.py` | Update internal imports |
| `src/corpus_inference_query/vector_store.py` | Rename env vars, update internal imports |
| `pyproject.toml` | Rename project, console entry, package directive |
| `tests/test_search.py` | Update imports, env vars, shorthand references |
| `tests/test_server.py` | Update imports, env vars, shorthand references |
| `scripts/install_local.sh` | Update package name references |
| `scripts/test.sh` | Update references |
| `scripts/build_dist.sh` | Update references |
| `scripts/register_mcp.py` | Update references |
| `README.md` | Rewrite for writing-corpus framing; update env vars and examples |
| `.gitignore` | Verify (likely already correct) |

### Files to delete

None. Old `code_inference_query/__pycache__/` and `tests/__pycache__/` directories are cleaned by `git clean -fdX` or removed when their parent is renamed.

---

## Tasks

### Task 1: Initialize git repository

**Files:**
- `.git/` (new, via `git init`)
- `.gitignore` (verify content)

**Why first:** Every subsequent task ends in a commit. We need a repo to commit into.

- [ ] **Step 1: Confirm current state**

```bash
cd /Users/amoscoletti/personal_dev/corpus-inference-query
ls -la
```
Expected: shows `src/`, `tests/`, `scripts/`, `pyproject.toml`, `README.md`, `PROJECT_PLAN.md`, `uv.lock`. **No `.git/` directory.**

- [ ] **Step 2: Verify .gitignore is sane**

```bash
cat .gitignore
```
Expected output (should include at minimum):
```
.venv/
__pycache__/
*.pyc
dist/
.pytest_cache/
```

If the file is missing any of those, edit it to match.

- [ ] **Step 3: Init the repo**

```bash
cd /Users/amoscoletti/personal_dev/corpus-inference-query
git init -b main
```
Expected: `Initialized empty Git repository in .../corpus-inference-query/.git/`

- [ ] **Step 4: Stage and commit baseline (the pre-rename clone)**

```bash
git add -A
git status --porcelain | head -20
```
Expected: list of files staged for initial commit. No surprises like `.venv/` or `__pycache__/`.

- [ ] **Step 5: Make the baseline commit**

```bash
git commit -m "$(cat <<'EOF'
chore: import code-inference-query as baseline for corpus-inference-query

Imported from /Users/amoscoletti/personal_dev/code-inference-query/.
This commit captures the starting state before M1 rename/refactor.
EOF
)"
```
Expected: commit succeeds; `git log --oneline` shows one commit.

---

### Task 2: Pin Python version and verify test runner

**Files:**
- `pyproject.toml:6` (no edit; just verify `requires-python = ">=3.11"` already correct)

**Why:** Run the existing test suite once before any changes to confirm we have a known-good baseline.

- [ ] **Step 1: Ensure a venv exists with the right deps**

```bash
cd /Users/amoscoletti/personal_dev/corpus-inference-query
bash ./scripts/install_local.sh
```
Expected: creates `.venv/` and installs `code-inference-query` plus dev deps. No errors.

- [ ] **Step 2: Run the existing test suite (baseline)**

```bash
./.venv/bin/pytest -q
```
Expected: tests collected and run. Vector tests may skip if `[vector]` extras are not installed — that's fine. **All non-skipped tests must pass.** If anything fails, stop and diagnose before continuing — M1 must not start on a red baseline.

- [ ] **Step 3: Record baseline test count**

Note the test count from Step 2 output (e.g., "12 passed, 3 skipped"). Subsequent tasks must keep this count green.

No commit needed for this task — read-only verification.

---

### Task 3: Add `style_tags` and `type_tags` to `CorpusSpec` (TDD)

**Files:**
- Test: `tests/test_search.py` (add a new test)
- Modify: `src/code_inference_query/corpus_config.py:10-18`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_search.py`, after the existing imports (around line 9):

```python
def test_corpus_spec_carries_style_and_type_tags() -> None:
    from code_inference_query.corpus_config import CorpusSpec
    import re

    spec = CorpusSpec(
        corpus_id="htws",
        shorthand="HTWS",
        relative_path="references/fish-howtowriteasentence/",
        section_pattern=re.compile(r"^# (.+)$"),
        description="How to Write a Sentence",
        is_directory=True,
        style_tags=["subordinating"],
        type_tags=["essay", "book"],
    )
    assert spec.style_tags == ["subordinating"]
    assert spec.type_tags == ["essay", "book"]


def test_corpus_spec_defaults_tags_to_empty_lists() -> None:
    from code_inference_query.corpus_config import CorpusSpec
    import re

    spec = CorpusSpec(
        corpus_id="x",
        shorthand="X",
        relative_path="x.md",
        section_pattern=re.compile(r"."),
    )
    assert spec.style_tags == []
    assert spec.type_tags == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
./.venv/bin/pytest tests/test_search.py::test_corpus_spec_carries_style_and_type_tags -v
```
Expected: `TypeError: CorpusSpec.__init__() got an unexpected keyword argument 'style_tags'`

- [ ] **Step 3: Add the fields to `CorpusSpec`**

In `src/code_inference_query/corpus_config.py`, modify the `CorpusSpec` dataclass to add two new fields after `is_directory`:

```python
@dataclass
class CorpusSpec:
    corpus_id: str
    shorthand: str
    relative_path: str
    section_pattern: re.Pattern
    subsection_pattern: re.Pattern | None = None
    description: str = ""
    is_directory: bool = False
    style_tags: list[str] = field(default_factory=list)
    type_tags: list[str] = field(default_factory=list)
```

(`field` is already imported at top of file.)

- [ ] **Step 4: Run both new tests to verify they pass**

```bash
./.venv/bin/pytest tests/test_search.py::test_corpus_spec_carries_style_and_type_tags tests/test_search.py::test_corpus_spec_defaults_tags_to_empty_lists -v
```
Expected: both PASS.

- [ ] **Step 5: Run full suite to verify nothing regressed**

```bash
./.venv/bin/pytest -q
```
Expected: still green (same count as Task 2 baseline + 2 new passing tests).

- [ ] **Step 6: Commit**

```bash
git add src/code_inference_query/corpus_config.py tests/test_search.py
git commit -m "feat(corpus_config): add style_tags and type_tags to CorpusSpec"
```

---

### Task 4: Add `style_tags` and `type_tags` to `Section` (TDD)

**Files:**
- Test: `tests/test_search.py`
- Modify: `src/code_inference_query/indexer.py:12-22`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_search.py`:

```python
def test_section_carries_style_and_type_tags() -> None:
    from code_inference_query.indexer import Section

    sec = Section(
        corpus_id="htws",
        shorthand="HTWS",
        chapter="Subordinating",
        section_name="Subordinating",
        citation="HTWS §Subordinating",
        content="The most controlled sentence in English.",
        line_start=1,
        keywords={"controlled", "sentence"},
        style_tags=["subordinating"],
        type_tags=["essay"],
    )
    assert sec.style_tags == ["subordinating"]
    assert sec.type_tags == ["essay"]


def test_section_defaults_tags_to_empty_lists() -> None:
    from code_inference_query.indexer import Section

    sec = Section(
        corpus_id="x",
        shorthand="X",
        chapter="C",
        section_name="S",
        citation="X §S",
        content="x",
        line_start=0,
    )
    assert sec.style_tags == []
    assert sec.type_tags == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
./.venv/bin/pytest tests/test_search.py::test_section_carries_style_and_type_tags -v
```
Expected: `TypeError: Section.__init__() got an unexpected keyword argument 'style_tags'`

- [ ] **Step 3: Add the fields to `Section`**

In `src/code_inference_query/indexer.py:12-22`, modify the `Section` dataclass:

```python
@dataclass
class Section:
    corpus_id: str
    shorthand: str
    chapter: str
    section_name: str
    citation: str
    content: str
    line_start: int
    keywords: set[str] = field(default_factory=set)
    style_tags: list[str] = field(default_factory=list)
    type_tags: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Run new tests**

```bash
./.venv/bin/pytest tests/test_search.py::test_section_carries_style_and_type_tags tests/test_search.py::test_section_defaults_tags_to_empty_lists -v
```
Expected: both PASS.

- [ ] **Step 5: Run full suite**

```bash
./.venv/bin/pytest -q
```
Expected: green.

- [ ] **Step 6: Commit**

```bash
git add src/code_inference_query/indexer.py tests/test_search.py
git commit -m "feat(indexer): add style_tags and type_tags to Section"
```

---

### Task 5: Rename package directory `code_inference_query` → `corpus_inference_query`

**Files:**
- Move: `src/code_inference_query/` → `src/corpus_inference_query/`

**Why ordered now:** the field additions in Tasks 3-4 are safer to do under the old name first, then we move atomically.

- [ ] **Step 1: Clear caches first to avoid stale `.pyc` confusion**

```bash
cd /Users/amoscoletti/personal_dev/corpus-inference-query
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
```
Expected: no errors.

- [ ] **Step 2: Move the package via git**

```bash
git mv src/code_inference_query src/corpus_inference_query
git status --porcelain
```
Expected: a list of renames `R  src/code_inference_query/X -> src/corpus_inference_query/X` for every file under the package.

- [ ] **Step 3: Update internal absolute imports inside the package**

The package imports `from .corpus_config import ...` (relative) — those will continue to work after rename. But test files import `from code_inference_query.indexer import Section` (absolute) — those will break. We fix tests in Task 8 after pyproject is updated. For now, do not run the test suite — it will fail until Tasks 6-8 complete.

No commit yet; this rename is incomplete until pyproject + tests are updated.

---

### Task 6: Update `pyproject.toml` for new package and console entry

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update project name, scripts, packages, description**

Replace the relevant fields in `pyproject.toml`:

```toml
[project]
name = "corpus-inference-query"
version = "0.1.0"
description = "MCP server for querying a writing corpus by shorthand citation, natural language, style, type, or standards violation"
readme = "README.md"
requires-python = ">=3.11"
dependencies = ["mcp>=1.0,<2.0"]

[project.optional-dependencies]
dev = ["build==1.5.0", "pytest==8.4.2"]
vector = ["lancedb>=0.3,<1.0", "fastembed>=0.2,<0.4"]

[project.scripts]
corpus-inference-query = "corpus_inference_query.server:main"

[build-system]
requires = ["hatchling>=1.0,<2.0"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/corpus_inference_query"]

[tool.ruff]
line-length = 88

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "C4", "SIM", "RUF"]
ignore = ["E501"]

[tool.mypy]
strict = true
ignore_missing_imports = true
show_error_codes = true
```

- [ ] **Step 2: Reinstall the package under the new name**

```bash
./.venv/bin/pip install -e .
```
Expected: installs `corpus-inference-query 0.1.0`. May show warnings about `code-inference-query` being installed alongside — that's the old version we'll uninstall next.

- [ ] **Step 3: Uninstall the old package name**

```bash
./.venv/bin/pip uninstall -y code-inference-query
```
Expected: `Successfully uninstalled code-inference-query-0.1.0`. If "package not found", that's also fine.

- [ ] **Step 4: Verify the new console entry exists**

```bash
ls .venv/bin/corpus-inference-query
.venv/bin/corpus-inference-query --help 2>&1 | head -5
```
Expected: file exists; `--help` either prints help or errors with a corpus-missing message — both are acceptable. (We have not yet updated the env var or fixture corpus.)

No commit yet — wait until tests pass (Task 8).

---

### Task 7: Rename env vars and MCP server name in `server.py` and `vector_store.py`

**Files:**
- Modify: `src/corpus_inference_query/server.py:19-28`
- Modify: `src/corpus_inference_query/vector_store.py` (env var references)

- [ ] **Step 1: Find every env var reference**

```bash
grep -rn "CODE_INFERENCE_" src/corpus_inference_query/ tests/
```
Expected: list of usages in `server.py`, `vector_store.py`, and tests. Capture for next step.

- [ ] **Step 2: Update `server.py` env vars and MCP server name**

In `src/corpus_inference_query/server.py`:

- Replace `CODE_INFERENCE_CORPUS_PATH` → `CORPUS_INFERENCE_PATH` (around line 24)
- Replace the `_DEFAULT_CORPUS_PATH` value: change `~/Library/Mobile Documents/com~apple~CloudDocs/code-inference` to `~/Documents/writing-corpus`
- Replace the error message reference `Set CODE_INFERENCE_CORPUS_PATH` → `Set CORPUS_INFERENCE_PATH` (around line 69)
- Replace `FastMCP("code-inference-query")` → `FastMCP("corpus-inference-query")` (around line 28)

Exact updated block:

```python
_DEFAULT_CORPUS_PATH = os.path.expanduser("~/Documents/writing-corpus")
CORPUS_PATH = Path(
    os.path.expanduser(
        os.environ.get("CORPUS_INFERENCE_PATH", _DEFAULT_CORPUS_PATH)
    )
)

mcp = FastMCP("corpus-inference-query")
```

And the error message:

```python
raise RuntimeError(
    f"Corpus path does not exist: {CORPUS_PATH}\n"
    f"Set CORPUS_INFERENCE_PATH to the correct location."
)
```

- [ ] **Step 3: Update `vector_store.py` env vars**

```bash
grep -n "CODE_INFERENCE_" src/corpus_inference_query/vector_store.py
```
Expected: usages of `CODE_INFERENCE_CACHE_PATH` and `CODE_INFERENCE_EMBED_MODEL`.

Replace:
- `CODE_INFERENCE_CACHE_PATH` → `CORPUS_INFERENCE_CACHE_PATH`
- `CODE_INFERENCE_EMBED_MODEL` → `CORPUS_INFERENCE_EMBED_MODEL`
- Cache directory default: `~/.cache/code-inference-query/lance` → `~/.cache/corpus-inference-query/lance`

- [ ] **Step 4: Verify no stale references remain in src/**

```bash
grep -rn "CODE_INFERENCE_\|code-inference-query\|code_inference_query" src/
```
Expected: **no matches.** (If any remain, fix them.)

No commit yet — wait for tests to pass.

---

### Task 8: Update test files for renamed package and env vars

**Files:**
- Modify: `tests/test_search.py`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Replace all `code_inference_query` imports**

```bash
sed -i.bak 's/code_inference_query/corpus_inference_query/g' tests/test_search.py tests/test_server.py
rm tests/test_search.py.bak tests/test_server.py.bak
```

- [ ] **Step 2: Replace env var references in tests**

In `tests/test_server.py` line ~13:
```python
os.environ.setdefault(
    "CORPUS_INFERENCE_PATH",
    os.path.join(os.path.dirname(__file__), "fixtures", "corpus"),
)
```

In `tests/test_search.py` `vector_env` fixture (lines 157-165):
```python
@pytest.fixture()
def vector_env(tmp_path):
    cache = str(tmp_path / "lance")
    os.environ["CORPUS_INFERENCE_CACHE_PATH"] = cache
    import corpus_inference_query.vector_store as vs
    vs._embed_model = None
    yield
    del os.environ["CORPUS_INFERENCE_CACHE_PATH"]
    vs._embed_model = None
```

- [ ] **Step 3: Verify no stale references remain in tests/**

```bash
grep -rn "CODE_INFERENCE_\|code_inference_query" tests/
```
Expected: **no matches.**

- [ ] **Step 4: Run full suite**

```bash
./.venv/bin/pytest -q
```
Expected: still green (same count as Task 4 baseline). The existing tests still reference code-corpus shorthands like `CC-Py`, `FP2e`, etc. — those tests construct `Section` objects in-place and don't actually load the corpus, so they pass regardless of `CORPUS_SPECS` content. We address shorthand renames in Task 10.

- [ ] **Step 5: Commit the rename + env-var update**

```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor: rename package code_inference_query -> corpus_inference_query

- Move src/code_inference_query/ -> src/corpus_inference_query/
- Update pyproject.toml: project name, console script, package directive
- Rename env vars: CODE_INFERENCE_* -> CORPUS_INFERENCE_*
- Update MCP server name: "code-inference-query" -> "corpus-inference-query"
- Default corpus path: ~/Documents/writing-corpus
- Update test imports and env var references
EOF
)"
```

---

### Task 9: Create fixture writing-corpus content

**Files:**
- Create: `tests/fixtures/corpus/corpus.toml`
- Create: `tests/fixtures/corpus/references/fish-howtowriteasentence/ch01.md`
- Create: `tests/fixtures/corpus/references/strunk-elements-of-style/omit-needless-words.md`

- [ ] **Step 1: Remove the old code-corpus fixture content**

```bash
ls tests/fixtures/corpus/ 2>/dev/null
```
If the fixture directory exists with old content (e.g., `clean-code-python/`, `fluent_python/`), remove them:

```bash
rm -rf tests/fixtures/corpus/clean-code-python tests/fixtures/corpus/fluent_python \
       tests/fixtures/corpus/google-coding-standards tests/fixtures/corpus/clean-code-inference \
       tests/fixtures/corpus/design-patterns-python tests/fixtures/corpus/example-code-2e 2>/dev/null || true
mkdir -p tests/fixtures/corpus/references/fish-howtowriteasentence
mkdir -p tests/fixtures/corpus/references/strunk-elements-of-style
```

- [ ] **Step 2: Create the placeholder `corpus.toml`**

`tests/fixtures/corpus/corpus.toml`:

```toml
# Placeholder writing-corpus manifest.
# M1: not parsed (specs are still hardcoded in corpus_config.py).
# M2: replaced by a real loader that reads this file.

[[source]]
shorthand = "HTWS"
path = "references/fish-howtowriteasentence/"
title = "How to Write a Sentence (fixture stub)"
author = "Stanley Fish"
year = 2011
default_style = ["subordinating"]
default_type = ["essay", "book"]

[[source]]
shorthand = "Strunk"
path = "references/strunk-elements-of-style/"
title = "Elements of Style (fixture stub)"
author = "Strunk and White"
year = 1959
default_style = []
default_type = ["essay"]
```

- [ ] **Step 3: Create the HTWS fixture content**

`tests/fixtures/corpus/references/fish-howtowriteasentence/ch01.md`:

```markdown
# Subordinating

The subordinating style arranges its parts in relations of dependency. One clause governs another; causality, time, and precedence are made visible in the syntax.

# Additive

The additive style strings its parts side by side. And and and. The reader follows by accumulation, not by hierarchy.
```

- [ ] **Step 4: Create the Strunk fixture content**

`tests/fixtures/corpus/references/strunk-elements-of-style/omit-needless-words.md`:

```markdown
# Omit Needless Words

Vigorous writing is concise. A sentence should contain no unnecessary words, a paragraph no unnecessary sentences, for the same reason that a drawing should have no unnecessary lines and a machine no unnecessary parts.
```

- [ ] **Step 5: Verify directory tree**

```bash
find tests/fixtures/corpus -type f
```
Expected: 3 files listed (corpus.toml + 2 markdown stubs).

- [ ] **Step 6: Commit the fixture corpus**

```bash
git add tests/fixtures/corpus/
git commit -m "test(fixtures): add writing-corpus stub (HTWS + Strunk) for M1+"
```

---

### Task 10: Replace `CORPUS_SPECS` with writing-corpus stubs

**Files:**
- Modify: `src/corpus_inference_query/corpus_config.py` (the `CORPUS_SPECS` list)
- Update: `tests/test_search.py` (existing tests that reference code-corpus shorthands need updating OR can be left alone because they construct Section objects in-place — see Step 1)

- [ ] **Step 1: Audit existing tests for hardcoded code-corpus references**

```bash
grep -n "CC-Py\|FP2e\|Google\|DP-Py\|clean-code-python\|fluent-python\|google-coding-standards\|design-patterns-python\|example-code-2e\|clean-code-inference" tests/
```

Most existing tests construct `Section` objects in-place (not via `build_index`), so they continue to work regardless of `CORPUS_SPECS`. The exception is any test that calls `build_index` against the fixture directory — verify by reading `tests/test_server.py` `TestReload` class.

Decision: keep the existing in-place `Section` constructions in `test_search.py` (they test scoring/parsing logic, not the spec list). Add new tests in Task 11 that use HTWS/Strunk shorthands.

- [ ] **Step 2: Replace the `CORPUS_SPECS` list**

In `src/corpus_inference_query/corpus_config.py`, replace the entire `CORPUS_SPECS` block (lines 22-70 in the original) with:

```python
CORPUS_SPECS: list[CorpusSpec] = [
    CorpusSpec(
        corpus_id="how-to-write-a-sentence",
        shorthand="HTWS",
        relative_path="references/fish-howtowriteasentence/",
        section_pattern=re.compile(r"^# (.+)$"),
        description="How to Write a Sentence — Stanley Fish (fixture stub)",
        is_directory=True,
        style_tags=["subordinating", "additive"],
        type_tags=["essay", "book"],
    ),
    CorpusSpec(
        corpus_id="strunk-elements-of-style",
        shorthand="Strunk",
        relative_path="references/strunk-elements-of-style/",
        section_pattern=re.compile(r"^# (.+)$"),
        description="Elements of Style — Strunk and White (fixture stub)",
        is_directory=True,
        style_tags=[],
        type_tags=["essay"],
    ),
]
```

- [ ] **Step 3: Also clear or trim `SUBSECTION_BLOCKLIST`**

The existing blocklist contains entries like `"Translations"` and `"Credits"` that were code-corpus-specific. For M1, keep the generic ones and drop the obviously code-doc-specific entries. Replace with:

```python
SUBSECTION_BLOCKLIST = frozenset({
    "Table of Contents",
    "Note",
    "Tip",
    "Warning",
    "Image",
    "Introduction",
    "License",
})
```

- [ ] **Step 4: Verify the indexer's `_extract_heading` doesn't break**

Read `src/corpus_inference_query/indexer.py:79-89`. The function has special cases for `corpus_id == "google-coding-standards"` and `corpus_id == "clean-code-inference"`. Neither of those corpus IDs exist anymore, so the function falls through to the generic `else:` branch. That's correct — no change needed in `_extract_heading`. But the special-case branches are now dead code.

Decision: leave the special cases in place for M1 (they cost nothing and ripping them out is risky without coverage). M2 cleanup task can remove them.

- [ ] **Step 5: Run full suite to verify nothing breaks**

```bash
./.venv/bin/pytest -q
```
Expected: green. The existing tests continue to pass because they don't go through `build_index` for the corpus list.

- [ ] **Step 6: Commit**

```bash
git add src/corpus_inference_query/corpus_config.py
git commit -m "refactor(corpus_config): replace code-corpus specs with writing-corpus stubs (HTWS, Strunk)"
```

---

### Task 11: Add new tests that exercise the fixture writing-corpus

**Files:**
- Modify: `tests/test_search.py` (add tests)

- [ ] **Step 1: Write tests that load the fixture corpus via `build_index`**

Add to `tests/test_search.py`:

```python
def test_build_index_loads_htws_fixture(tmp_path) -> None:
    """build_index reads the fixture HTWS markdown and produces tagged sections."""
    from pathlib import Path
    from corpus_inference_query.indexer import build_index

    fixture_root = Path(__file__).parent / "fixtures" / "corpus"
    sections = build_index(fixture_root)

    htws = [s for s in sections if s.shorthand == "HTWS"]
    assert len(htws) >= 2  # Subordinating + Additive headings in the fixture
    assert any("Subordinating" in s.section_name for s in htws)
    assert any("Additive" in s.section_name for s in htws)


def test_build_index_loads_strunk_fixture() -> None:
    """build_index reads the Strunk fixture and emits an Omit Needless Words section."""
    from pathlib import Path
    from corpus_inference_query.indexer import build_index

    fixture_root = Path(__file__).parent / "fixtures" / "corpus"
    sections = build_index(fixture_root)

    strunk = [s for s in sections if s.shorthand == "Strunk"]
    assert len(strunk) >= 1
    assert any("Omit Needless Words" in s.section_name for s in strunk)
```

Note: these tests verify that `build_index` works against the new fixture corpus and the new `CORPUS_SPECS`. They do NOT yet test that `style_tags` propagate from CorpusSpec defaults onto produced Sections — that propagation is a feature added in M2 (via the `corpus.toml` loader). For M1, Section tags default to empty lists.

- [ ] **Step 2: Run the new tests to verify they fail**

```bash
./.venv/bin/pytest tests/test_search.py::test_build_index_loads_htws_fixture tests/test_search.py::test_build_index_loads_strunk_fixture -v
```
Expected: both FAIL with `assert 0 >= 2` (or similar) — `build_index` returns 0 sections for HTWS/Strunk.

**Why they fail:** `build_index` in `indexer.py:200-213` only handles `corpus_id == "design-patterns-python"` or `"example-code-2e"` when `is_directory=True`. Every other directory-corpus falls through the `continue` and is silently skipped. The HTWS and Strunk specs have `is_directory=True` but neither matches the hardcoded corpus_ids, so they're skipped entirely.

- [ ] **Step 3: Add a generic directory-corpus branch to `build_index`**

In `src/corpus_inference_query/indexer.py`, locate the `is_directory` block inside `build_index` (around lines 200-206) and add an `else:` branch:

```python
        if spec.is_directory:
            if spec.corpus_id == "design-patterns-python":
                all_sections.extend(_index_design_patterns(spec, corpus_path))
            elif spec.corpus_id == "example-code-2e":
                all_sections.extend(_index_example_code(spec, corpus_path))
            else:
                # Generic directory corpus: index every .md file under the
                # directory using the spec's section pattern.
                dir_path = corpus_path / spec.relative_path
                if dir_path.exists():
                    for md_file in sorted(dir_path.rglob("*.md")):
                        text = md_file.read_text(errors="replace")
                        all_sections.extend(_index_markdown_sections(spec, text))
            continue
```

- [ ] **Step 4: Re-run the new tests to verify they pass**

```bash
./.venv/bin/pytest tests/test_search.py::test_build_index_loads_htws_fixture tests/test_search.py::test_build_index_loads_strunk_fixture -v
```
Expected: both PASS.

- [ ] **Step 5: Run full suite**

```bash
./.venv/bin/pytest -q
```
Expected: green; new tests included.

- [ ] **Step 6: Commit**

```bash
git add src/corpus_inference_query/indexer.py tests/test_search.py
git commit -m "feat(indexer): generic directory-corpus loader + fixture HTWS/Strunk tests"
```

---

### Task 12: Update scripts to reference the new package and console entry

**Files:**
- Modify: `scripts/install_local.sh`
- Modify: `scripts/test.sh`
- Modify: `scripts/build_dist.sh`
- Modify: `scripts/register_mcp.py`

- [ ] **Step 1: Find all stale references in scripts/**

```bash
grep -rn "code-inference-query\|code_inference_query\|CODE_INFERENCE_" scripts/
```
Expected: list of usages. Update each one.

- [ ] **Step 2: Update `scripts/install_local.sh`**

Replace any `code-inference-query` reference with `corpus-inference-query`. The script likely echoes the package name in progress messages — just text changes.

- [ ] **Step 3: Update `scripts/test.sh` and `scripts/build_dist.sh`**

Same pattern: text replacements only. These scripts shouldn't reference the package internals.

- [ ] **Step 4: Update `scripts/register_mcp.py`**

This script registers the MCP into a Claude/Codex config. Replace:
- The MCP server key from `"code-inference-query"` to `"corpus-inference-query"`
- Any path containing `code-inference-query`
- Any env var `CODE_INFERENCE_CORPUS_PATH` → `CORPUS_INFERENCE_PATH`

- [ ] **Step 5: Verify scripts are clean**

```bash
grep -rn "code-inference-query\|code_inference_query\|CODE_INFERENCE_" scripts/
```
Expected: **no matches.**

- [ ] **Step 6: Smoke test install_local.sh**

```bash
rm -rf .venv  # remove the existing venv to test a clean install
bash ./scripts/install_local.sh
./.venv/bin/corpus-inference-query --help 2>&1 | head -5
```
Expected: install succeeds; `--help` either prints help or surfaces a corpus-missing error (acceptable — corpus path not set in shell).

- [ ] **Step 7: Run full suite once more**

```bash
./.venv/bin/pytest -q
```
Expected: green.

- [ ] **Step 8: Commit**

```bash
git add scripts/
git commit -m "refactor(scripts): update install/test/build/register scripts for new package name"
```

---

### Task 13: Rewrite `README.md` for the writing-corpus framing

**Files:**
- Modify: `README.md` (full rewrite)

- [ ] **Step 1: Write the new README**

Replace the entire `README.md` content with:

````markdown
# corpus-inference-query MCP Server

`corpus-inference-query` is a Python MCP server that indexes a **writing corpus** — reference works, exemplars by genre, and the user's personal writings — and returns relevant excerpts by shorthand citation, natural-language query, style/type filter, or standards-violation check.

## What This Repo Provides

- A stdio MCP server entry point: `corpus-inference-query`
- A lightweight local indexer over a writing-corpus directory
- Citation lookup for shorthands like `HTWS §Subordinating`
- Natural-language search across configured corpora
- (Coming in later milestones: standards-violation detection, exemplar retrieval, drafting aids)

## Repository Layout

```text
src/corpus_inference_query/
  server.py          MCP server entry point
  corpus_config.py   corpus manifest and shorthand definitions
  indexer.py         corpus loading and section indexing
  search.py          citation parsing and search formatting
  vector_store.py    optional vector search backend (requires [vector] extras)
standards/
  writing-standards.md   (authored in milestone M3)
scripts/
  install_local.sh   create a local venv and install the package
  build_dist.sh      build wheel and sdist artifacts
  test.sh            run the lightweight unit test suite
  register_mcp.py    register the MCP into a Claude/Codex config
tests/
  test_search.py     search smoke tests (includes vector store tests)
  test_server.py     MCP tool routing tests
  fixtures/corpus/   tiny writing-corpus fixture used by tests
docs/superpowers/
  specs/             design specs (the authoritative architecture document)
  plans/             implementation plans per milestone
```

## Prerequisites

- Python 3.11+
- A writing corpus directory at `CORPUS_INFERENCE_PATH` (default `~/Documents/writing-corpus`)

## Quick Start

```bash
cd /path/to/corpus-inference-query
bash ./scripts/install_local.sh
./.venv/bin/corpus-inference-query --help
```

Set `EDITABLE_INSTALL=1` for an editable install:

```bash
EDITABLE_INSTALL=1 bash ./scripts/install_local.sh
```

### Vector Search Extras (optional)

```bash
./.venv/bin/pip install -e ".[vector]"
```

Embeds the corpus on first NL query (~5–10s) and caches the index at `~/.cache/corpus-inference-query/lance/`. Cache is invalidated automatically when the corpus changes.

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `CORPUS_INFERENCE_PATH` | `~/Documents/writing-corpus` | Path to the writing corpus directory |
| `CORPUS_INFERENCE_CACHE_PATH` | `~/.cache/corpus-inference-query/lance` | Where the vector index is cached |
| `CORPUS_INFERENCE_EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | fastembed model name for vector search |

## MCP Configuration

```json
{
  "mcpServers": {
    "corpus-inference-query": {
      "type": "stdio",
      "command": "/absolute/path/to/.venv/bin/corpus-inference-query",
      "env": {
        "CORPUS_INFERENCE_PATH": "/absolute/path/to/writing-corpus"
      }
    }
  }
}
```

## Query Examples (M1 scope — limited)

| Query | Returns |
|---|---|
| `HTWS §Subordinating` | Fish, Subordinating chapter (fixture stub) |
| `Strunk §Omit Needless Words` | Strunk and White (fixture stub) |

Richer tooling (style/type filters, standards violations, exemplar retrieval, drafting aids) arrives in milestones M2–M6.

## Run Tests

```bash
bash ./scripts/test.sh
```

## Design Docs

The architecture and milestone plan live in `docs/superpowers/specs/` and `docs/superpowers/plans/`. Start with the design spec for any deeper work.
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs(readme): rewrite for writing-corpus framing"
```

---

### Task 14: Delete the stale `PROJECT_PLAN.md`

**Files:**
- Delete: `PROJECT_PLAN.md`

**Why:** It described the distribution plan for `code-inference-query`. The new architecture spec at `docs/superpowers/specs/2026-05-22-corpus-inference-query-design.md` supersedes it (and §1 of the spec explicitly notes "Supersedes: PROJECT_PLAN.md").

- [ ] **Step 1: Confirm contents are obsolete**

```bash
head -20 PROJECT_PLAN.md
```
Expected: the legacy distribution plan referencing `code-inference-query`.

- [ ] **Step 2: Delete and commit**

```bash
git rm PROJECT_PLAN.md
git commit -m "chore: remove PROJECT_PLAN.md (superseded by docs/superpowers/specs/2026-05-22 design)"
```

---

### Task 15: Final full-suite verification and milestone tag

- [ ] **Step 1: Clean caches and rerun the full suite**

```bash
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
./.venv/bin/pytest -q
```
Expected: green. Capture the final test count.

- [ ] **Step 2: Run ruff and mypy**

```bash
./.venv/bin/pip install ruff mypy 2>&1 | tail -2
./.venv/bin/ruff check src/ tests/
./.venv/bin/mypy --strict src/corpus_inference_query/
```
Expected: ruff: 0 errors (or only known/pre-existing ones — note them). mypy: 0 errors.

If either tool surfaces new errors introduced by M1 changes, fix them and re-run. If errors are pre-existing (also present in the baseline `code_inference_query` code), record them for an M2 cleanup task but do not fix in M1.

- [ ] **Step 3: Confirm the console entry runs**

```bash
./.venv/bin/corpus-inference-query --help 2>&1 | head -5
```
Expected: either help text or a clear "corpus path does not exist" message. Both indicate the binary is wired correctly.

- [ ] **Step 4: Inspect the git log**

```bash
git log --oneline
```
Expected: ~13 commits from M1, starting from the baseline import.

- [ ] **Step 5: Tag the milestone**

```bash
git tag -a m1-rename-scaffold -m "M1: rename to corpus_inference_query + two-axis tag scaffold"
git tag -l m1-rename-scaffold
```
Expected: tag created.

- [ ] **Step 6: Verify no stale references anywhere**

```bash
grep -rn "code-inference-query\|code_inference_query\|CODE_INFERENCE_" \
  --exclude-dir=.venv --exclude-dir=.git --exclude-dir=__pycache__ \
  --exclude-dir=.pytest_cache --exclude-dir=docs .
```
Expected: **no matches.** (The `docs/` directory is excluded because the spec intentionally documents the old/new mapping in §3.2.)

If any remain, fix them and amend the most recent relevant commit (`git commit --amend` is acceptable only because nothing has been pushed yet; once pushed, never amend published commits).

---

## Done Definition

M1 is complete when:

1. The package is `corpus_inference_query`; the old name appears nowhere outside the docs that intentionally cite it.
2. `corpus-inference-query --help` is installed and runs.
3. `CORPUS_SPECS` contains writing-corpus stubs (HTWS, Strunk) with `style_tags` and `type_tags` fields populated.
4. `CorpusSpec` and `Section` both carry `style_tags: list[str]` and `type_tags: list[str]` (default empty list).
5. The fixture corpus exists at `tests/fixtures/corpus/` and is loaded by `build_index`.
6. `pytest -q` is green.
7. The milestone is tagged `m1-rename-scaffold`.

After M1 is tagged, return for the M2 plan: real `corpus.toml` loader + MCP tool surface (find_exemplars, check_against_standards, find_similar_voice, suggest_opening, suggest_rewrite).

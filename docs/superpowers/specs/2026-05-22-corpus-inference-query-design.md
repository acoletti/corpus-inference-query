# corpus-inference-query — Design Spec

**Date:** 2026-05-22
**Status:** Approved for planning
**Author:** Brainstormed with Claude (Opus 4.7)
**Supersedes:** PROJECT_PLAN.md (the code-inference-query distribution plan)

---

## 1. Goal and Non-Goals

### Goal

Refactor the copied `corpus-inference-query/` directory (originally a clone of `code-inference-query`) into a Python MCP server that indexes a **writing corpus** — reference works, exemplars by genre, and the user's personal writings — and exposes citation lookup, natural-language search, exemplar retrieval, standards-violation detection, and retrieval-based drafting aids. The MCP composes with a new `/writing` skill and a refactored `/editorial-review` board to provide standards-grounded writing assistance.

### Non-Goals

- **Not a generative writing service.** The MCP performs retrieval only. No LLM calls inside the server, no API-key surface, no provider lock-in. Drafting suggestions are returned as ranked exemplar excerpts; calling skills compose the actual prose.
- **Not a public-facing tool.** The GitHub repo is private. The corpus contains copyrighted reference works and personal writings; neither will be redistributed.
- **Not a replacement for `/editorial-review`.** The MCP enriches the existing 3-phase editorial board with standards-aware synthesis; the persona-driven critique stays intact.
- **Not a packaged content corpus.** The MCP repo ships code + `writing-standards.md` only. The corpus content lives in a separate, user-managed directory.

---

## 2. Background

The source project (`code-inference-query`) is a Python stdio MCP that indexes a code corpus and exposes shorthand citation lookup (e.g., `CC-Py §Functions.2`) plus optional vector search (LanceDB + fastembed). Its architecture is sound and directly applicable to a prose corpus. This spec retains the architecture and substitutes the domain.

Stanley Fish's *How to Write a Sentence* (2011) provides the foundational sentence-style taxonomy: **Subordinating** (hypotactic), **Additive** (paratactic), **Satiric**, **First sentences**, **Last sentences**, and **Self-reflexive sentences**. Note: the "balanced" and "periodic" categories sometimes attributed to Fish are classical (Cicero, Quintilian) forms he references but does not adopt.

Document-level **types** (article, book, email, letter, technical doc, newsletter, op-ed, etc.) form a second, orthogonal axis. Every corpus excerpt carries both axes.

---

## 3. Architecture

### 3.1 Overview

- Python stdio MCP server (`mcp>=1.0,<2.0`).
- Optional vector backend (LanceDB + fastembed) gated behind `[vector]` extras.
- Corpus loaded from an external directory via env var; never bundled in the repo.
- Standards document (`writing-standards.md`) lives **inside** the repo (version-controlled with the detectors that test against it).

### 3.2 Repo rename plan

| Old (code MCP) | New (corpus MCP) |
|---|---|
| package `code_inference_query` | `corpus_inference_query` |
| console entry `code-inference-query` | `corpus-inference-query` |
| env `CODE_INFERENCE_CORPUS_PATH` | `CORPUS_INFERENCE_PATH` |
| env `CODE_INFERENCE_CACHE_PATH` | `CORPUS_INFERENCE_CACHE_PATH` |
| env `CODE_INFERENCE_EMBED_MODEL` | `CORPUS_INFERENCE_EMBED_MODEL` |
| default cache `~/.cache/code-inference-query/lance/` | `~/.cache/corpus-inference-query/lance/` |

Default corpus path: `~/Documents/writing-corpus/` (NOT iCloud — corpus contains private writings).

### 3.3 Corpus directory layout

The corpus directory is external to the repo. Recommended layout:

```
writing-corpus/
  corpus.toml                 # manifest: per-source metadata, shorthand prefix, style/type tags
  references/
    fish-howtowriteasentence/
    strunk-elements-of-style/
    zinsser-on-writing-well/
    williams-style/
    pinker-sense-of-style/
  exemplars/
    articles/
    essays/
    emails/
    letters/
    technical-docs/
    newsletters/
    op-eds/
    speeches/
  personal/                   # private writings, never redistributed
    blog-posts/
    emails/
    letters/
```

### 3.4 Two-axis tagging (style x type)

`corpus.toml` example:

```toml
[[source]]
shorthand = "HTWS"
path = "references/fish-howtowriteasentence/"
title = "How to Write a Sentence"
author = "Stanley Fish"
year = 2011
default_style = ["subordinating"]
default_type = ["essay", "book"]

[[source]]
shorthand = "PandP"
path = "references/austen-pride-and-prejudice/"
title = "Pride and Prejudice"
author = "Jane Austen"
year = 1813
default_style = ["subordinating"]
default_type = ["novel"]
```

Per-section overrides come from frontmatter at the top of each section file (YAML or TOML block). Sections inherit `default_style` / `default_type` if not overridden.

Recognized style tags: `subordinating`, `additive`, `satiric`, `first-sentence`, `last-sentence`, `self-reflexive`, `balanced` (classical), `periodic` (classical).

Recognized type tags: `book`, `memoir`, `essay`, `longform-journalism`, `white-paper`, `article`, `op-ed`, `blog-post`, `review`, `profile`, `explainer`, `email`, `letter`, `memo`, `cover-letter`, `newsletter`, `column`, `regular-blog`, `technical-doc`, `rfc`, `readme`, `runbook`, `api-doc`, `release-notes`, `copywriting`, `landing-page`, `sales-letter`, `pitch`, `speech`, `talk-transcript`, `sermon`, `short-story`, `novella`, `novel`.

### 3.5 Shorthand citation scheme

Mirrors code-inference-query exactly. Style and type are query-time filters, not citation components.

Examples:
- `HTWS §Subordinating.3` — Fish, Subordinating chapter, 3rd example
- `WS §1.2` — writing-standards.md, §1 Clarity, subsection 2
- `WS §A.3` — writing-standards.md, §A Article addendum, rule 3
- `Strunk §Omit` — Strunk & White, "Omit needless words"
- `PandP §opening` — *Pride and Prejudice* opening line

---

## 4. MCP Tool Surface

All tools are retrieval-only. No LLM calls inside the server.

### 4.0 Common return shape — `Excerpt`

Tools that return excerpts share a common JSON shape:

```jsonc
{
  "shorthand": "HTWS",                      // corpus shorthand prefix
  "citation": "HTWS §Subordinating.3",      // resolvable via lookup_citation
  "text": "...",                            // the excerpt content
  "style_tags": ["subordinating"],
  "type_tags": ["essay", "book"],
  "register": "L",                          // C|P|A|L (casual/professional/academic/literary)
  "score": 0.82,                            // 0-1, only present on similarity-based returns
  "metadata": {                             // optional, source-specific
    "author": "Stanley Fish",
    "title": "How to Write a Sentence",
    "section": "Subordinating"
  }
}
```

References below to `excerpt` and `first-sentence excerpt` use this shape; `first-sentence excerpt` adds an `is_opening: true` marker.

### 4.1 `list_corpora`
- **Signature:** `() -> [{shorthand, title, author, default_style, default_type, doc_count}]`
- **Purpose:** Discovery. Calling skills enumerate available corpora before querying.

### 4.2 `query`
- **Signature:** `(text: str, top_k: int = 8, style?: list[str], type?: list[str], corpus?: str) -> [{shorthand, citation, text, style_tags, type_tags, score}]`
- **Purpose:** NL search across the configured corpora. `style` and `type` are filter facets (intersection semantics). `corpus` narrows to one shorthand.

### 4.3 `lookup_citation`
- **Signature:** `(citation: str) -> {shorthand, citation, text, style_tags, type_tags}`
- **Purpose:** Resolve a shorthand citation like `HTWS §Subordinating.3` to its excerpt.

### 4.4 `find_exemplars`
- **Signature:** `(style?: list[str], type?: list[str], length?: 'short'|'medium'|'long', register?: 'C'|'P'|'A'|'L', top_k: int = 5) -> [excerpt]`
- **Purpose:** "Show me 5 short additive openings appropriate for a casual newsletter." Retrieval over the tagged corpus by facet combination.

### 4.5 `check_against_standards`
- **Signature:** `(text: str, types?: list[str]) -> [{rule_id, rule_title, severity, span, snippet, exemplar_citation, suggested_rewrite_from_exemplar}]`
- **Purpose:** Match `text` against `writing-standards.md` rules. **Mechanical detection only** — one Python detector per `§`-rule, using heuristics (regex, vector cosine, sentence-length distributions). Severity: `error | warning | info`. The "suggested rewrite" is an **exemplar from the corpus**, not generated prose.
- **Auto-detection:** if `types` is omitted, the server infers likely types from text shape (length, register, structural markers) and applies both universal §1-§15 and matching type addenda §A-§J.
- **Graceful skip:** detectors whose requirements aren't met return `null` for that rule rather than raising. Specifically: §13 Voice fidelity skips when the personal corpus is empty; §7 Audience fit skips when no `type` can be inferred and none was provided; vector-based detectors skip when the `[vector]` extra is not installed. Skipped rules surface in a `skipped_rules` array on the response, with reason codes (`personal_corpus_empty`, `type_unknown`, `vector_backend_unavailable`).

### 4.6 `find_similar_voice`
- **Signature:** `(text: str, top_k: int = 5, corpus: str = 'personal') -> [excerpt]`
- **Purpose:** "Write more like me." Vector-similarity search against the personal corpus (or any specified corpus shorthand). No-ops gracefully if the named corpus is empty.

### 4.7 `suggest_opening`
- **Signature:** `(type: str, style?: str, topic?: str, top_k: int = 5) -> [first-sentence excerpt]`
- **Purpose:** Retrieval-only drafting aid. Returns first-sentences from the corpus matching the target type/style/topic. Calling skill composes the actual opening.

### 4.8 `suggest_rewrite`
- **Signature:** `(text: str, target_style: str, top_k: int = 5) -> [exemplar passage]`
- **Purpose:** Retrieval-only. Returns exemplar passages in `target_style` of similar length/topic. Calling skill performs the rewrite using exemplars as in-context shaping.

### 4.9 `reload`
- **Signature:** `() -> {status, corpora_count, doc_count}`
- **Purpose:** Re-index after corpus changes. Same as code-inference-query.

---

## 5. `writing-standards.md` — Structure

Lives at `standards/writing-standards.md` inside the repo. Each rule entry includes: title, principle, mechanical detector description, exemplar citation, anti-pattern example, corrected example.

### 5.1 Universal sections (§1-§15)

| § | Title | Anchored in | Detector heuristic |
|---|---|---|---|
| §1 | Clarity (one-pass reading) | Williams, Pinker | sentences with >2 nested clauses + ambiguous antecedents |
| §2 | Cohesion (old → new) | Williams *Style* | sentence-pair subject continuity check |
| §3 | Concision | Strunk, Zinsser | redundancy patterns; doubled adjectives |
| §4 | Voice / agency | Williams, Pinker | passive-voice rate >25% per paragraph; nominalization density |
| §5 | Diction and register | Garner *MEU* | register mismatch; jargon without gloss |
| §6 | Sentence rhythm | Fish, Zinsser | sentence-length std-dev outside acceptable band |
| §7 | Audience fit | Pinker | Flesch-Kincaid outside band for declared `type` |
| §8 | Argument honesty | Pinker *Sense of Style* | hedge clusters; unsupported intensifiers |
| §9 | Opening craft (angle of lean) | Fish | first sentence ≤25 words; presence of hook (action verb / question / surprise) |
| §10 | Closing craft | Fish | last sentence resolves an opener-introduced thread (vector check) |
| §11 | Concrete over abstract | Zinsser, Strunk | abstract-noun rate; missing exemplification |
| §12 | Style consciousness | Fish | dominant-style classifier (additive/subordinating/mixed); flag drift across paragraphs |
| §13 | Voice fidelity | personal corpus | cosine to personal corpus below threshold (gated on personal corpus existing) |
| §14 | Transitions | Williams | connector density; missing transitions at section boundaries |
| §15 | Lede and title craft | journalistic | title length; nut-graf presence for `type=article` |

### 5.2 Type addenda (§A-§J)

| § | Type | Rules (4-6 per addendum) |
|---|---|---|
| §A | Article | nut graf within first 3 paragraphs; sourced quotes; inverted-pyramid (news) or scene-led (feature) |
| §B | Email | subject predicts body; ≤3 paragraphs; explicit ask in first 2 sentences; clear closing action |
| §C | Letter | salutation; one occasion; addressee acknowledged; sign-off appropriate to register |
| §D | Technical doc / RFC | context-first; numbered sections; alternatives considered; risks listed; precise terminology |
| §E | Newsletter | consistent opener; ≤1 main thread per issue; CTA / subscribe loop; voice continuity |
| §F | Op-ed | one claim in first paragraph; called-out stakes; ≤1200 words; bylined-expertise hook |
| §G | Blog post | scannable subheads every ~300 words; conversational register acceptable; link-as-citation |
| §H | White paper | executive summary; numbered sections; citations; explicit recommendation |
| §I | Memo | TO/FROM/RE; BLUF (bottom line up front); bullet support; ≤4 pages |
| §J | Speech / talk | short sentences (median <18 words); audience addressed; tricolons / repetition; oral cadence |

### 5.3 Annex X — Shorthand-table conventions

Documents how new corpus sources get a shorthand prefix and how to tag style/type. Lives alongside the main standards content.

---

## 6. Skill and Workflow Integration

### 6.1 New skill: `/writing`

Files:
- `~/.claude/commands/writing.md` — slash command entry
- `~/.claude/writing/templates/` — drafting templates (one per type)
- `~/.claude/writing/personas/` — optional voice personas (deferred to a later iteration)

Invocation: `/writing <type> <topic-or-prompt>`. Example: `/writing email re: declining a vendor meeting`.

Phases:
1. **Brief** — classify the request (`type`, optional `style`, audience, length target). One clarifying question only if `type` is ambiguous.
2. **Retrieve** — call MCP `find_exemplars(type, style?, register?)`, `suggest_opening(type, style?)`, optionally `find_similar_voice(prior_user_text)`.
3. **Draft** — Claude composes the draft using retrieved exemplars as in-context shaping. The MCP does not generate.
4. **Self-review** — call MCP `check_against_standards(draft, types=[type])`. Apply fixes for `error` severity; surface `warning` severity.
5. **Deliver** — final draft + list of consulted §-rules and exemplar citations.

### 6.2 Refactored workflow: `/editorial-review`

Existing 3-phase board (Woolf / Tolstoy / Fish / Steinbeck personas → debate → synthesis) becomes standards-aware.

- **Phase 1 (persona reviews):** persona templates updated to optionally consult MCP via `lookup_citation` (self-references — Fish persona quotes the actual book) and `find_exemplars(style=persona-style)` (comparators). Behavior backward-compatible: skips MCP calls if the server is not registered.
- **Phase 2 (debate):** unchanged structurally.
- **Phase 3 (synthesis):** synthesis template rewritten. Final Editorial Report adds a **Standards Violations** section sourced from `check_against_standards(writing, types=auto)` — §-citations and corpus-exemplar rewrites presented alongside persona-driven critique.

Template files affected:
- `~/.claude/editorial-review/templates/review.md` (Phase 1 persona prompt — adds MCP consultation block)
- `~/.claude/editorial-review/templates/synthesis.md` (Phase 3 — adds standards-violation section)
- `~/.claude/editorial-review/personas/*.md` (light edits to invite MCP consultation; persona voice intact)

No new template files ship from the `corpus-inference-query` repo itself. The MCP only ships the server and `writing-standards.md`.

---

## 7. Gutenberg Seeding

The corpus is bootstrapped from Project Gutenberg using the existing extractor in `/Volumes/jane/mindmonkey_audio` (CLI: `mindmonkey-audio extract gutenberg --id <BOOK_ID> --output <path>`).

### 7.1 Script: `scripts/seed_gutenberg.py`

Thin wrapper that:
1. Reads a manifest `scripts/gutenberg_seed.toml` listing `(book_id, author, work, style_tags, type_tags, target_path)` entries.
2. For each entry, shells out to `mindmonkey-audio extract gutenberg --id <id> --output <target_path> --split-chapters --clean`.
3. Writes / appends matching `[[source]]` blocks to the user's `writing-corpus/corpus.toml`.
4. Logs successes, skips already-present entries, surfaces failures with the Gutenberg URL for manual diagnosis.

**Seed-time runtime requirements:**
- The `/Volumes/jane/mindmonkey_audio` external volume must be mounted (the script preflight checks the path and prints a clear "volume not mounted; mount and retry" message if missing).
- The `mindmonkey-audio` CLI must be on `PATH` or its absolute path supplied via `MINDMONKEY_AUDIO_BIN` env var.
- Network access to `gutenberg.org` (the wrapped extractor handles the HTTP).

`mindmonkey-audio` is a seed-time dependency only — not required at MCP runtime, not declared in `pyproject.toml`.

### 7.2 Initial seed manifest (candidates; book IDs to verify at seed time)

| Style | Author / Work | Candidate PG ID |
|---|---|---|
| Subordinating | Austen, *Pride and Prejudice* | 1342 |
| Subordinating | Austen, *Emma* | 158 |
| Subordinating | James, *The Turn of the Screw* | 209 |
| Subordinating | Dickens, *A Tale of Two Cities* | 98 |
| Subordinating | Wharton, *The Age of Innocence* | 541 |
| Additive | Stein, *Three Lives* | 15408 |
| Additive | Ford, *The Good Soldier* | 2775 |
| Additive | Whitman, *Leaves of Grass* (prose passages) | 1322 |
| Satiric | Swift, *A Modest Proposal* | 1080 |
| Satiric | Swift, *Gulliver's Travels* | 829 |
| Satiric | Wilde, *The Picture of Dorian Gray* | 174 |
| First-sentence | (cross-extracted from above) | — |

Woolf and Hemingway are largely US-copyrighted — sourced separately or via Fish quote excerpts (fair use).

---

## 8. Repo, CI, Testing

### 8.1 GitHub repo

- Name: `corpus-inference-query`
- Visibility: **private**
- License: MIT (internal)
- Layout (same shape as code-inference-query):

```
corpus-inference-query/
  src/corpus_inference_query/
    server.py
    corpus_config.py
    indexer.py
    search.py
    vector_store.py
    detectors/               # standards-rule detection code
      __init__.py
      rules.py               # one function per §-rule
      registry.py            # maps §-id -> detector function
  scripts/
    install_local.sh
    build_dist.sh
    test.sh
    register_mcp.py
    seed_gutenberg.py
    gutenberg_seed.toml
  standards/
    writing-standards.md
  tests/
    test_search.py
    test_server.py
    test_standards.py
    test_seed_gutenberg.py
    fixtures/
      corpus/                # tiny tagged fixture corpus
  docs/
    superpowers/
      specs/
        2026-05-22-corpus-inference-query-design.md  # this file
  pyproject.toml
  README.md
  .gitignore
  .github/workflows/ci.yml
```

`.gitignore`: `.venv/`, `__pycache__/`, `dist/`, `.pytest_cache/`, `*.lock` (allow `uv.lock`).

### 8.2 CI (GitHub Actions, single workflow)

- `ruff check` + `ruff format --check`
- `mypy --strict src/`
- `pytest -q` (without `[vector]` extras for speed)
- `pip install -e .` then `corpus-inference-query --help` smoke
- Matrix: Python 3.11, 3.12 on `ubuntu-latest`

### 8.3 Testing strategy

- Existing patterns extended for two-axis tagging and new tools (`tests/test_search.py`, `tests/test_server.py`).
- `tests/test_standards.py` — one test per §-rule detector with positive/negative fixtures.
- `tests/test_seed_gutenberg.py` — dry-run test that the seeder builds correct `corpus.toml` entries (network mocked).
- `tests/fixtures/corpus/` — tiny tagged fixture corpus shared by all retrieval tests.

---

## 9. Phasing / Milestones

Each milestone is independently shippable and sized to fit one `/implement` slice (≤12 units).

| M | Title | Description | Approx units |
|---|---|---|---|
| M1 | Rename + scaffold | Package rename, env-var rename, console-entry rename, two-axis schema in `corpus_config.py`, fixture corpus stub, tests green | 6-8 |
| M2 | Tool surface | Implement all 9 MCP tools against the fixture corpus; each tool unit-tested | 9-11 |
| M3 | Standards doc v1 | Author §1-§15 + §A-§J in `writing-standards.md`; one detector per rule with fixture-based tests | 10-12 |
| M4 | Gutenberg seeding | `scripts/seed_gutenberg.py` calling mindmonkey-audio; populate real corpus from `gutenberg_seed.toml` | 4-6 |
| M5 | Editorial-review refactor | Synthesis template rev, persona prompt edits, integration tests | 4-6 |
| M6 | `/writing` skill | New skill files in `~/.claude/`; end-to-end test (email, op-ed, technical doc) | 5-7 |
| M7 | CI + private GitHub repo | Push, CI green, README polish | 3-5 |

---

## 10. Open Questions / Deferred Work

- **Persona drafting voices for `/writing`** (deferred from M6). Optional voice personas (e.g., "draft this email in your professional tone vs. casual tone") use `find_similar_voice` against personal-corpus subdirectories tagged by voice.
- **Multilingual corpus support.** Current scope is English-only. fastembed multilingual models exist but are not part of v1.
- **Citation-format normalization.** If we add more reference works with different shorthand conventions, we may need a citation-style registry. Out of scope for v1.
- **Detector accuracy bake-off.** Some §-rule detectors (especially §1 Clarity, §12 Style consciousness) are inherently heuristic. v1 ships with conservative thresholds; tune from real writing samples in a follow-up.
- **`/editorial-review` standards synthesis ergonomics.** First version surfaces all violations. If output is too noisy, add severity filtering to the synthesis template in a follow-up.

# M3: Writing Standards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Author `standards/writing-standards.md` (§1–§15 universal + §A–§J type addenda), implement one mechanical Python detector per rule, wire detectors into `CorpusRepository.check_against_standards`, and update the MCP tool response formatter.

**Architecture:** A `detectors/` package contains `base.py` (dataclasses), `rules.py` (one function per §-rule), and `registry.py` (maps §-id → function, exposes `run_all()`). `CorpusRepository.check_against_standards` delegates to `registry.run_all()` and returns `{violations, skipped_rules, types_detected}`. All detectors are pure functions (no I/O, no corpus access) except §13 Voice Fidelity, which always returns `None` (skip) in M3 pending M6.

**Tech Stack:** Python 3.11+, `re`, `statistics` (stdlib only — no third-party NLP deps in M3).

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `standards/writing-standards.md` | **Create** | Authoritative rule doc (§1–§15 + §A–§J). Versioned with the detectors. |
| `src/corpus_inference_query/detectors/__init__.py` | **Create** | Package re-export: `Violation`, `SkipResult`, `run_all` |
| `src/corpus_inference_query/detectors/base.py` | **Create** | `Violation` + `SkipResult` dataclasses; `DetectorFn` type alias |
| `src/corpus_inference_query/detectors/rules.py` | **Create** | One `detect_*` function per §-rule; shared helpers (`_split_sentences`, `_content_words`, etc.) |
| `src/corpus_inference_query/detectors/registry.py` | **Create** | `UNIVERSAL_DETECTORS`, `TYPE_DETECTORS`, `_TYPE_TO_ANNEX`, `run_all()` |
| `src/corpus_inference_query/corpus_repository.py` | **Modify** | Replace stub `check_against_standards` with `registry.run_all()` delegation |
| `src/corpus_inference_query/tool_responses.py` | **Modify** | Replace `format_check_stub` with `format_check_results` (formats real violations) |
| `src/corpus_inference_query/server.py` | **Modify** | Update `check_against_standards` tool to call `format_check_results` |
| `tests/test_standards.py` | **Create** | Positive + negative test per §-rule detector |
| `tests/test_tool_responses.py` | **Modify** | Replace stub test with `format_check_results` tests |
| `tests/test_server.py` | **Modify** | Update `check_against_standards` mock/integration expectations |

---

## Interfaces (locked before Task 3)

### `Violation` (from `base.py`)
```python
@dataclass
class Violation:
    rule_id: str          # e.g. "§1"
    rule_title: str       # e.g. "Clarity"
    severity: str         # "error" | "warning" | "info"
    snippet: str          # offending excerpt (≤120 chars)
    span: tuple[int, int] | None = None        # char positions in original text
    exemplar_citation: str | None = None       # filled by corpus lookup (M4+)
    suggested_rewrite_from_exemplar: str | None = None
```

### `SkipResult` (from `base.py`)
```python
@dataclass
class SkipResult:
    rule_id: str
    rule_title: str
    reason: str  # "personal_corpus_empty" | "type_unknown" | "vector_backend_unavailable"
```

### `DetectorFn` (from `base.py`)
```python
DetectorFn = Callable[[str, list[str] | None], list[Violation] | None]
# Returns:
#   []              — rule ran, no violations
#   [Violation(...)] — violations found
#   None            — rule skipped (caller records SkipResult)
```

### `run_all()` return shape (from `registry.py`)
```python
{
    "violations": [
        {
            "rule_id": "§3",
            "rule_title": "Concision",
            "severity": "warning",
            "snippet": "due to the fact that",
            "span": [42, 62],
            "exemplar_citation": None,
            "suggested_rewrite_from_exemplar": None,
        }
    ],
    "skipped_rules": [
        {"rule_id": "§13", "rule_title": "Voice Fidelity", "reason": "personal_corpus_empty"}
    ],
    "types_used": ["essay"],      # types actually applied
}
```

---

## Task 1: `standards/writing-standards.md`

**Files:**
- Create: `standards/writing-standards.md`

- [ ] **Step 1: Create the standards directory and file**

```bash
mkdir -p standards
```

- [ ] **Step 2: Write the standards document**

Create `standards/writing-standards.md` with the content below. Each entry follows the format: **§N Title**, Principle, Detector heuristic, Anti-pattern, Correction. Exemplar citations are placeholders (real citations filled when corpus is seeded in M4).

```markdown
# Writing Standards

Version-controlled alongside the detector code in `corpus-inference-query`.
Each §-section maps to one detector function in `src/corpus_inference_query/detectors/rules.py`.

---

## Universal Rules (§1–§15)

Apply to all writing types unless otherwise noted.

---

### §1 Clarity (one-pass reading)

**Principle:** A reader should understand each sentence on first pass. Sentences exceeding 40 words or containing more than two nested relative clauses require the reader to backtrack.

**Detector:** Flag sentences with >40 words OR more than two occurrences of `which`, `who`, `that`, `whom`, `whose` within a single sentence.

**Severity:** warning

**Anti-pattern:**
> The committee, which had been formed by the board, which itself had been appointed by the shareholders who had voted at the annual meeting that was held in March, decided to defer.

**Correction:**
> The committee deferred the decision. It had been formed by a board appointed by shareholders at the March annual meeting.

**Exemplar citation:** (pending corpus seed — M4)

---

### §2 Cohesion (old → new)

**Principle:** Each sentence should begin with an element the reader already knows (the "topic") and move toward new information (the "stress"). When sentence N+1 opens with an entirely new subject, readers lose the thread.

**Detector:** For each consecutive sentence pair, check whether the content words of sentence N+1 share at least one word with sentence N. Flag pairs with zero overlap.

**Severity:** info

**Anti-pattern:**
> The experiment failed. Astronauts aboard the station reported unusual readings.

**Correction:**
> The experiment failed. The failure was first noticed when astronauts reported unusual readings.

**Exemplar citation:** (pending corpus seed — M4)

---

### §3 Concision

**Principle:** Remove words that duplicate meaning. Wordy phrases have leaner equivalents; doubled adjectives repeat what a single word already says.

**Detector:** Regex match for known wordy-phrase patterns:
- "in the event that" → "if"
- "due to the fact that" → "because"
- "at this point in time" → "now"
- "in order to" → "to"
- "very unique" → "unique"
- "completely finished" → "finished"
- "final outcome" → "outcome"
- "future plans" → "plans"
- "past history" → "history"
- "refer back" → "refer"
- "end result" → "result"
- "basic fundamentals" → "fundamentals"

**Severity:** warning

**Anti-pattern:**
> Due to the fact that the report was late, the team was forced to meet at this point in time.

**Correction:**
> Because the report was late, the team met now.

**Exemplar citation:** (pending corpus seed — M4)

---

### §4 Voice and Agency

**Principle:** Active sentences foreground who acts. When more than 25% of sentences in a paragraph use passive constructions, the prose buries agency.

**Detector:** Count passive-voice constructions per paragraph using the pattern `\b(was|were|is|are|am|been|be)\s+\w+(?:ed|en)\b`. Flag paragraphs where passive sentences exceed 25% of total sentences.

Also flag nominalization density: more than 20% of content words ending in `-tion`, `-ness`, `-ment`, `-ity`.

**Severity:** warning

**Anti-pattern:**
> The decision was made by the committee. The report was reviewed and approved. The findings were communicated to stakeholders.

**Correction:**
> The committee decided. They reviewed and approved the report, then informed stakeholders.

**Exemplar citation:** (pending corpus seed — M4)

---

### §5 Diction and Register

**Principle:** Vocabulary should match the audience and occasion. Casual markers in formal contexts and formal markers in casual contexts both create friction.

**Detector:** Flag casual register markers (`kinda`, `gonna`, `wanna`, `gotta`, `awesome`, `totally`, `literally`, `basically`) when the declared type is a formal type (`technical-doc`, `rfc`, `white-paper`, `memo`, `letter`). Flag hedge-free declaratives in academic or persuasive contexts.

**Severity:** warning

**Anti-pattern (formal type, casual register):**
> The system is gonna be totally awesome once we fix this.

**Correction:**
> The system will perform significantly better once this issue is resolved.

**Exemplar citation:** (pending corpus seed — M4)

---

### §6 Sentence Rhythm

**Principle:** Prose that varies sentence length holds attention. Paragraphs where every sentence is the same length become monotonous; paragraphs with extreme length variation feel choppy.

**Detector:** Per paragraph (≥3 sentences): compute sentence-length standard deviation. Flag if std-dev < 3 words (too uniform) or mean > 35 words with std-dev < 8 (uniformly long).

**Severity:** info

**Anti-pattern (uniform, monotonous):**
> The report was late. The team was frustrated. The client was unhappy. The manager intervened.

**Correction:**
> The report was late, which frustrated the team and alarmed the client. The manager stepped in.

**Exemplar citation:** (pending corpus seed — M4)

---

### §7 Audience Fit (Flesch-Kincaid)

**Principle:** Reading level should match the declared audience. Technical docs can be complex; emails and newsletters should be accessible.

**Detector:** Compute Flesch Reading Ease (FRE) score. Compare to expected range by type:
- `email`, `letter`, `newsletter`, `blog-post`: FRE 60–80
- `technical-doc`, `rfc`, `white-paper`, `memo`: FRE 30–60
- `speech`, `talk-transcript`: FRE 70–90
- `op-ed`, `article`, `essay`: FRE 50–70

Skip if `types` is empty or None (skip reason: `type_unknown`).

**FRE formula:** `206.835 − 1.015×(words/sentences) − 84.6×(syllables/words)`

**Severity:** info

**Anti-pattern (email, FRE 25):**
> The multifaceted ramifications of the aforementioned contractual obligations necessitate immediate remediation.

**Correction:**
> This contract issue needs to be fixed right away.

**Exemplar citation:** (pending corpus seed — M4)

---

### §8 Argument Honesty

**Principle:** Good arguments make explicit claims. Hedge clusters weaken credibility; bare intensifiers assert without proof.

**Detector:** Flag hedge clusters (≥3 of: `seems`, `appears`, `arguably`, `perhaps`, `possibly`, `might`, `could`, `may` within 50 words). Flag bare intensifiers: `obviously`, `clearly`, `certainly`, `everyone knows`, `it is clear`, `needless to say`.

**Severity:** warning

**Anti-pattern:**
> It perhaps seems like the proposal could possibly work, though it arguably might need more thought.

**Correction:**
> The proposal has merit, but requires further analysis before implementation.

**Exemplar citation:** (pending corpus seed — M4)

---

### §9 Opening Craft

**Principle:** A first sentence should be ≤25 words and contain a hook: an action verb, a question, or a surprising element. A first sentence that begins with "I will" or "This paper" announces itself rather than engaging.

**Detector:** Check first sentence word count (flag if >25 words). Flag if first sentence begins with a throat-clearing pattern: `^(This|In this|The purpose of|I will|This paper|This essay|In this paper)`.

**Severity:** warning

**Anti-pattern:**
> This paper will discuss the importance of sentence craft in the development of an engaging writing style.

**Correction:**
> Sentences make readers.

**Exemplar citation:** (pending corpus seed — M4)

---

### §10 Closing Craft

**Principle:** The last sentence should resolve, not trail off. Summative openers (`In conclusion`, `To summarize`) are redundant — the position itself signals closure.

**Detector:** Check last sentence for summative opener patterns: `^(In conclusion|To summarize|In summary|To conclude|As I have shown|As we have seen|Thus, it can be seen)`.

**Severity:** warning

**Anti-pattern:**
> In conclusion, it is clear that sentence craft is important for all writers.

**Correction:**
> Sentences are the writer's only material.

**Exemplar citation:** (pending corpus seed — M4)

---

### §11 Concrete Over Abstract

**Principle:** Readers understand specifics faster than generalities. Abstract nouns (ending in `-tion`, `-ness`, `-ment`, `-ity`, `-ism`) at high density signal that concrete examples are missing.

**Detector:** Count words matching `\b\w+(?:tion|ness|ment|ity|ism|ance|ence)\b` (case-insensitive) and divide by total content words. Flag if density > 25%.

**Severity:** info

**Anti-pattern:**
> The achievement of organizational transformation requires commitment to the implementation of foundational improvements.

**Correction:**
> Organizations change when leaders commit to specific, visible reforms.

**Exemplar citation:** (pending corpus seed — M4)

---

### §12 Style Consciousness

**Principle:** A dominant sentence style — additive (coordination) or subordinating (hypotaxis) — shapes the reader's experience. Unintentional style drift within a piece creates an incoherent voice.

**Detector:** Per paragraph: count sentences opening with coordinating conjunctions (`And|But|Or|Yet|So`) as additive markers; count sentences opening with subordinating conjunctions (`Although|Because|Since|While|Unless|If|When|Before|After|Though`) as subordinating markers. Flag if the dominant style switches across consecutive paragraphs (e.g., ≥3 additive in P1, ≥3 subordinating in P2).

**Severity:** info

**Anti-pattern (style drift):**
> P1: "And the river rose. And the banks broke. And the town flooded."
> P2: "Although the waters receded, since the damage had been done, the recovery, which was slow, required intervention."

**Correction:** Choose one dominant style per piece; switch styles only for deliberate effect.

**Exemplar citation:** (pending corpus seed — M4)

---

### §13 Voice Fidelity

**Principle:** Personal writing should sound like the writer. Cosine distance from one's own corpus signals voice drift.

**Detector:** Vector-similarity search against the `personal` corpus. Flag sections below a similarity threshold (0.6).

**M3 status:** Always skipped. Requires vector backend + populated personal corpus. Skip reason: `personal_corpus_empty`.

**Severity:** info

**Exemplar citation:** (pending corpus seed — M4)

---

### §14 Transitions

**Principle:** Readers need bridges between ideas. Paragraphs that begin with no reference to the preceding paragraph create jarring leaps.

**Detector:** Check paragraph openings for transition markers: `however`, `therefore`, `furthermore`, `moreover`, `additionally`, `consequently`, `nevertheless`, `thus`, `hence`, `meanwhile`, `subsequently`, `conversely`, `for example`, `in contrast`, `on the other hand`, `that said`, `in other words`. Flag sequences of ≥3 consecutive paragraphs (≥2 sentences each) with no transition markers.

**Severity:** info

**Anti-pattern:**
> P1: Dogs are loyal animals.
> P2: The history of Rome spans centuries.
> P3: Quantum computing is advancing rapidly.

**Correction:** Add transitions or restructure so each paragraph follows from the previous.

**Exemplar citation:** (pending corpus seed — M4)

---

### §15 Lede and Title Craft

**Principle:** For articles: the nut graf (the "so what") should appear within the first three paragraphs. A title should preview the piece in ≤15 words.

**Detector:**
1. If text opens with a title line (first line ≤120 chars, followed by blank line), flag if title is >15 words.
2. For `type=article`: check first three paragraphs for stakes language (`why`, `matters`, `means`, `impact`, `effect`, `result`, `important`, `significant`). Flag if none found.

Skip step 2 if `types` is empty (skip reason: `type_unknown`).

**Severity:** warning (title length), info (nut graf)

**Anti-pattern (title):**
> "A Comprehensive Survey of the Current State of Sentence-Level Writing Craft Research in Contemporary Academic Literature"

**Correction:**
> "The Science of the Sentence"

**Exemplar citation:** (pending corpus seed — M4)

---

## Type Addenda (§A–§J)

Applied when `types` includes the matching type tag. All type addenda are severity `warning` unless noted.

---

### §A Article

Types: `article`, `longform-journalism`

| Rule | Detector |
|------|----------|
| A.1 Nut graf | First 3 paragraphs contain stakes language (see §15 detector, already implemented) |
| A.2 Sourced quotes | Quoted text (regex: `"[^"]+"`) has attribution within 20 words (`said`, `according to`, `wrote`, `noted`, `reported`) |
| A.3 Word count | 400–5000 words; flag if shorter or longer |
| A.4 Lead type | First paragraph ≤3 sentences (news inverted pyramid) or opens with scene/anecdote (feature) |

---

### §B Email

Types: `email`

| Rule | Detector |
|------|----------|
| B.1 Length | ≤3 paragraphs (flag if more) |
| B.2 Explicit ask | First 2 sentences contain `?` or an imperative verb (`Please`, `Could you`, `Can you`, `I need`, `Let me know`) |
| B.3 Subject line | If text opens with `Subject:`, flag subject >12 words |
| B.4 Closing action | Final sentence contains action language (`let me know`, `please reply`, `I'll follow up`, `confirm by`) |

---

### §C Letter

Types: `letter`, `cover-letter`

| Rule | Detector |
|------|----------|
| C.1 Salutation | Text contains `Dear` within first 3 lines |
| C.2 Sign-off | Text ends with closing phrase (`Sincerely`, `Best regards`, `Respectfully`, `Yours`) |
| C.3 Single occasion | Flag if text contains more than 2 distinct topic-shift markers (`Regarding`, `On another note`, `Additionally`) |

---

### §D Technical Doc / RFC

Types: `technical-doc`, `rfc`, `readme`, `runbook`, `api-doc`

| Rule | Detector |
|------|----------|
| D.1 Context first | First paragraph does not start with code/command (no backtick or `$` in first 100 chars) |
| D.2 Numbered sections | Flag if text is >500 words and contains no numbered headings (regex: `^\d+\.` or `^#{1,3}`) |
| D.3 Alternatives | Text ≥800 words contains `alternative`, `instead`, `trade-off`, `trade off`, `option`, or `approach` |
| D.4 Terminology | Flag if any term appears in all-caps >3 times and is never followed by parenthetical definition |

---

### §E Newsletter

Types: `newsletter`

| Rule | Detector |
|------|----------|
| E.1 CTA/subscribe | Text contains `subscribe`, `unsubscribe`, or `forward this` |
| E.2 Single thread | Flag if more than 3 `##` section headings (single newsletter = single main topic) |
| E.3 Voice continuity | Opening and closing paragraphs share register (both casual or both formal, detected by casual-marker density) |

---

### §F Op-ed

Types: `op-ed`

| Rule | Detector |
|------|----------|
| F.1 Claim in first paragraph | First paragraph contains a claim verb: `should`, `must`, `is wrong`, `is right`, `needs to`, `ought to` |
| F.2 Stakes | First 3 paragraphs contain stakes language (see §15/A.1 pattern) |
| F.3 Word count | 600–1200 words; flag if outside this range |
| F.4 Credibility hook | First 5 sentences contain `I`, `we`, `my`, or `our` (writer's stake / bylined expertise) |

---

### §G Blog Post

Types: `blog-post`, `regular-blog`

| Rule | Detector |
|------|----------|
| G.1 Subheads | For posts >300 words: at least one `##` or `###` heading per 400 words |
| G.2 Register | Casual register acceptable: at least one sentence with conversational markers (`I`, `you`, `we`, `here's`, `let's`) |
| G.3 Link citation | For posts >500 words: flag if no hyperlink pattern (`[text](url)` or bare `http`) present |

---

### §H White Paper

Types: `white-paper`

| Rule | Detector |
|------|----------|
| H.1 Executive summary | Text contains `executive summary` or `abstract` (case-insensitive) within first 200 chars |
| H.2 Numbered sections | Text ≥1000 words has numbered headings (regex: `^\d+\.`) |
| H.3 Recommendation | Text contains `recommend`, `we propose`, `our recommendation`, or `proposed solution` |
| H.4 Citations | Text ≥800 words has at least one citation marker: `[1]`, `(Author`, or `—` footnote dash |

---

### §I Memo

Types: `memo`

| Rule | Detector |
|------|----------|
| I.1 Header | Text contains `TO:` and `FROM:` and `RE:` (or `SUBJECT:`) within first 5 lines |
| I.2 BLUF | First sentence after header is a declarative statement (not a question) |
| I.3 Bullets | Contains at least one list marker (`- `, `* `, or `\d+\.`) |
| I.4 Length | ≤1800 words (≈4 pages) |

---

### §J Speech / Talk

Types: `speech`, `talk-transcript`

| Rule | Detector |
|------|----------|
| J.1 Short sentences | Median sentence length ≤18 words |
| J.2 Audience address | Contains `you`, `we`, `our`, `your` (direct address) |
| J.3 Tricolon | Contains at least one tricolon pattern: three parallel phrases separated by commas (`X, Y, and Z` where X/Y/Z are similar syntactic units ≥3 words each) |
| J.4 Sentence variety for oral cadence | At least 20% of sentences ≤8 words (short punchy sentences for oral delivery) |

---

## Annex X — Shorthand-table conventions

When adding a new corpus source:
1. Choose a unique shorthand (2–8 uppercase letters or title abbreviation)
2. Add `[[source]]` block to `writing-corpus/corpus.toml`
3. Assign `default_style` from: `subordinating`, `additive`, `satiric`, `first-sentence`, `last-sentence`, `self-reflexive`, `balanced`, `periodic`
4. Assign `default_type` from the full type list in the design spec §3.4
5. Per-section overrides go in YAML/TOML frontmatter at the top of section files
```

- [ ] **Step 3: Verify the file was written**

```bash
wc -l standards/writing-standards.md
```
Expected: ~250+ lines

- [ ] **Step 4: Commit**

```bash
git add standards/writing-standards.md
git commit -m "docs(standards): author writing-standards.md §1–§15 and §A–§J"
```

---

## Task 2: Detector Infrastructure

**Files:**
- Create: `src/corpus_inference_query/detectors/__init__.py`
- Create: `src/corpus_inference_query/detectors/base.py`
- Create: `src/corpus_inference_query/detectors/registry.py`
- Create: `src/corpus_inference_query/detectors/rules.py` (scaffold only — helpers + empty stubs)
- Create: `tests/test_standards.py` (scaffold + smoke test)

- [ ] **Step 1: Write the failing smoke test**

Create `tests/test_standards.py`:

```python
"""Tests for writing-standards detectors."""
from __future__ import annotations

import pytest

from corpus_inference_query.detectors import run_all
from corpus_inference_query.detectors.base import Violation


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
```

- [ ] **Step 2: Run to confirm it fails**

```bash
.venv/bin/pytest tests/test_standards.py::TestRegistry -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'corpus_inference_query.detectors'`

- [ ] **Step 3: Create `detectors/base.py`**

```python
"""Violation and SkipResult dataclasses for standards detectors."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Violation:
    rule_id: str
    rule_title: str
    severity: str  # "error" | "warning" | "info"
    snippet: str
    span: tuple[int, int] | None = None
    exemplar_citation: str | None = None
    suggested_rewrite_from_exemplar: str | None = None


@dataclass
class SkipResult:
    rule_id: str
    rule_title: str
    reason: str  # "personal_corpus_empty" | "type_unknown" | "vector_backend_unavailable"


DetectorFn = Callable[[str, "list[str] | None"], "list[Violation] | None"]
```

- [ ] **Step 4: Create `detectors/rules.py` scaffold (helpers only, stubs for each rule)**

```python
"""Writing-standards detectors — one function per §-rule."""
from __future__ import annotations

import re
import statistics

from .base import Violation

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_SENT_END_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z\"\'])')
_STOP_WORDS = frozenset([
    'the', 'a', 'an', 'in', 'of', 'to', 'and', 'for', 'is', 'was',
    'are', 'it', 'this', 'that', 'with', 'by', 'at', 'be', 'as',
    'on', 'or', 'not', 'but', 'from', 'has', 'had', 'have', 'its',
])


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_END_RE.split(text) if s.strip()]


def _content_words(text: str) -> list[str]:
    return [
        w.lower().strip('.,!?;:()"\'')
        for w in text.split()
        if w.lower().strip('.,!?;:()"\'') not in _STOP_WORDS
    ]


def _count_syllables(word: str) -> int:
    word = word.lower().strip('.,!?;:()"\' ')
    if not word:
        return 0
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in 'aeiou'
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith('e') and count > 1:
        count -= 1
    return max(1, count)


def _flesch_reading_ease(text: str) -> float:
    sentences = _split_sentences(text)
    if not sentences:
        return 100.0
    words = text.split()
    if not words:
        return 100.0
    syllable_count = sum(_count_syllables(w) for w in words)
    asl = len(words) / len(sentences)
    asw = syllable_count / len(words)
    return 206.835 - 1.015 * asl - 84.6 * asw


# ---------------------------------------------------------------------------
# Universal rules §1–§15 (stubs — filled in Tasks 3–6)
# ---------------------------------------------------------------------------

def detect_clarity(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_cohesion(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_concision(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_voice_agency(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_diction_register(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_sentence_rhythm(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_audience_fit(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_argument_honesty(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_opening_craft(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_closing_craft(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_concrete_abstract(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_style_consciousness(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_voice_fidelity(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return None  # always skip in M3 — requires personal corpus vector search


def detect_transitions(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_lede_and_title(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


# ---------------------------------------------------------------------------
# Type addenda §A–§J (stubs — filled in Tasks 7–8)
# ---------------------------------------------------------------------------

def detect_article(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_email(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_letter(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_technical_doc(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_newsletter(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_op_ed(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_blog_post(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_white_paper(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_memo(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []


def detect_speech(text: str, types: list[str] | None = None) -> list[Violation] | None:
    return []
```

- [ ] **Step 5: Create `detectors/registry.py`**

```python
"""Detector registry: maps §-id → function; exposes run_all()."""
from __future__ import annotations

from .base import DetectorFn, SkipResult, Violation
from . import rules as _r

_TYPE_TO_ANNEX: dict[str, str] = {
    "article": "§A",
    "longform-journalism": "§A",
    "email": "§B",
    "letter": "§C",
    "cover-letter": "§C",
    "technical-doc": "§D",
    "rfc": "§D",
    "readme": "§D",
    "runbook": "§D",
    "api-doc": "§D",
    "newsletter": "§E",
    "op-ed": "§F",
    "blog-post": "§G",
    "regular-blog": "§G",
    "white-paper": "§H",
    "memo": "§I",
    "speech": "§J",
    "talk-transcript": "§J",
}

UNIVERSAL_DETECTORS: dict[str, tuple[str, DetectorFn]] = {
    "§1": ("Clarity", _r.detect_clarity),
    "§2": ("Cohesion", _r.detect_cohesion),
    "§3": ("Concision", _r.detect_concision),
    "§4": ("Voice and Agency", _r.detect_voice_agency),
    "§5": ("Diction and Register", _r.detect_diction_register),
    "§6": ("Sentence Rhythm", _r.detect_sentence_rhythm),
    "§7": ("Audience Fit", _r.detect_audience_fit),
    "§8": ("Argument Honesty", _r.detect_argument_honesty),
    "§9": ("Opening Craft", _r.detect_opening_craft),
    "§10": ("Closing Craft", _r.detect_closing_craft),
    "§11": ("Concrete Over Abstract", _r.detect_concrete_abstract),
    "§12": ("Style Consciousness", _r.detect_style_consciousness),
    "§13": ("Voice Fidelity", _r.detect_voice_fidelity),
    "§14": ("Transitions", _r.detect_transitions),
    "§15": ("Lede and Title Craft", _r.detect_lede_and_title),
}

TYPE_DETECTORS: dict[str, tuple[str, DetectorFn]] = {
    "§A": ("Article", _r.detect_article),
    "§B": ("Email", _r.detect_email),
    "§C": ("Letter", _r.detect_letter),
    "§D": ("Technical Doc", _r.detect_technical_doc),
    "§E": ("Newsletter", _r.detect_newsletter),
    "§F": ("Op-Ed", _r.detect_op_ed),
    "§G": ("Blog Post", _r.detect_blog_post),
    "§H": ("White Paper", _r.detect_white_paper),
    "§I": ("Memo", _r.detect_memo),
    "§J": ("Speech", _r.detect_speech),
}

_SKIP_REASONS: dict[str, str] = {
    "§13": "personal_corpus_empty",
    "§7": "type_unknown",
}


def run_all(text: str, types: list[str] | None = None) -> dict:
    """Run all applicable detectors; return {violations, skipped_rules, types_used}."""
    violations: list[dict] = []
    skipped: list[dict] = []

    for rule_id, (title, fn) in UNIVERSAL_DETECTORS.items():
        if rule_id == "§7" and not types:
            skipped.append({"rule_id": rule_id, "rule_title": title, "reason": "type_unknown"})
            continue
        result = fn(text, types)
        if result is None:
            reason = _SKIP_REASONS.get(rule_id, "not_applicable")
            skipped.append({"rule_id": rule_id, "rule_title": title, "reason": reason})
        else:
            violations.extend(_violation_to_dict(v) for v in result)

    # Type-specific addenda
    applicable_annexes: set[str] = set()
    if types:
        for t in types:
            annex = _TYPE_TO_ANNEX.get(t)
            if annex:
                applicable_annexes.add(annex)

    for annex_id in sorted(applicable_annexes):
        title, fn = TYPE_DETECTORS[annex_id]
        result = fn(text, types)
        if result is None:
            skipped.append({"rule_id": annex_id, "rule_title": title, "reason": "not_applicable"})
        else:
            violations.extend(_violation_to_dict(v) for v in result)

    return {
        "violations": violations,
        "skipped_rules": skipped,
        "types_used": types or [],
    }


def _violation_to_dict(v: Violation) -> dict:
    return {
        "rule_id": v.rule_id,
        "rule_title": v.rule_title,
        "severity": v.severity,
        "snippet": v.snippet,
        "span": list(v.span) if v.span else None,
        "exemplar_citation": v.exemplar_citation,
        "suggested_rewrite_from_exemplar": v.suggested_rewrite_from_exemplar,
    }
```

- [ ] **Step 6: Create `detectors/__init__.py`**

```python
"""Writing-standards violation detectors."""
from .base import DetectorFn, SkipResult, Violation
from .registry import run_all

__all__ = ["DetectorFn", "SkipResult", "Violation", "run_all"]
```

- [ ] **Step 7: Run the smoke test**

```bash
.venv/bin/pytest tests/test_standards.py::TestRegistry -v
```
Expected: PASS (2 tests)

- [ ] **Step 8: Run full suite to confirm no regressions**

```bash
.venv/bin/pytest -q
```
Expected: 110 passed, 3 skipped (adds 2 new tests)

- [ ] **Step 9: Commit**

```bash
git add src/corpus_inference_query/detectors/ tests/test_standards.py
git commit -m "feat(detectors): scaffold detector package — base types, registry, rule stubs"
```

---

## Task 3: §1–§4 Universal Detectors

**Files:**
- Modify: `src/corpus_inference_query/detectors/rules.py` (fill in §1–§4 stubs)
- Modify: `tests/test_standards.py` (add §1–§4 test classes)

- [ ] **Step 1: Write failing tests for §1–§4**

Add to `tests/test_standards.py`:

```python
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
```

Add these imports at the top of `tests/test_standards.py` (below existing imports):

```python
from corpus_inference_query.detectors.rules import (
    detect_clarity,
    detect_cohesion,
    detect_concision,
    detect_voice_agency,
)
```

- [ ] **Step 2: Run to confirm they fail**

```bash
.venv/bin/pytest tests/test_standards.py::TestClarity tests/test_standards.py::TestCohesion tests/test_standards.py::TestConcision tests/test_standards.py::TestVoiceAgency -v
```
Expected: ~11 FAIL — stubs return `[]`

- [ ] **Step 3: Implement `detect_clarity` in `rules.py`**

Replace the stub:

```python
_RELATIVE_CLAUSE_RE = re.compile(r'\b(which|who|that|whom|whose)\b', re.I)

def detect_clarity(text: str, types: list[str] | None = None) -> list[Violation] | None:
    violations = []
    for sent in _split_sentences(text):
        words = sent.split()
        relative_clauses = len(_RELATIVE_CLAUSE_RE.findall(sent))
        if len(words) > 40 or relative_clauses > 2:
            violations.append(Violation(
                rule_id="§1",
                rule_title="Clarity",
                severity="warning",
                snippet=sent[:120],
            ))
    return violations
```

- [ ] **Step 4: Implement `detect_cohesion` in `rules.py`**

```python
def detect_cohesion(text: str, types: list[str] | None = None) -> list[Violation] | None:
    sentences = _split_sentences(text)
    if len(sentences) < 2:
        return []
    violations = []
    for i in range(1, len(sentences)):
        prev = set(_content_words(sentences[i - 1]))
        curr = set(_content_words(sentences[i]))
        if prev and curr and not (prev & curr):
            violations.append(Violation(
                rule_id="§2",
                rule_title="Cohesion",
                severity="info",
                snippet=sentences[i][:120],
            ))
    return violations
```

- [ ] **Step 5: Implement `detect_concision` in `rules.py`**

```python
_WORDY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\bin the event that\b', re.I), 'if'),
    (re.compile(r'\bdue to the fact that\b', re.I), 'because'),
    (re.compile(r'\bat this point in time\b', re.I), 'now'),
    (re.compile(r'\bin order to\b', re.I), 'to'),
    (re.compile(r'\bvery unique\b', re.I), 'unique'),
    (re.compile(r'\bcompletely finished\b', re.I), 'finished'),
    (re.compile(r'\bfinal outcome\b', re.I), 'outcome'),
    (re.compile(r'\bfuture plans\b', re.I), 'plans'),
    (re.compile(r'\bpast history\b', re.I), 'history'),
    (re.compile(r'\brefer back\b', re.I), 'refer'),
    (re.compile(r'\bend result\b', re.I), 'result'),
    (re.compile(r'\bbasic fundamentals\b', re.I), 'fundamentals'),
]

def detect_concision(text: str, types: list[str] | None = None) -> list[Violation] | None:
    violations = []
    for pattern, suggestion in _WORDY_PATTERNS:
        for m in pattern.finditer(text):
            violations.append(Violation(
                rule_id="§3",
                rule_title="Concision",
                severity="warning",
                snippet=f'"{m.group()}" → "{suggestion}"',
                span=(m.start(), m.end()),
            ))
    return violations
```

- [ ] **Step 6: Implement `detect_voice_agency` in `rules.py`**

```python
_PASSIVE_RE = re.compile(r'\b(was|were|is|are|am|been|be)\s+\w+(?:ed|en)\b', re.I)
_ABSTRACT_NOUN_RE = re.compile(r'\b\w+(?:tion|ness|ment|ity|ism|ance|ence)\b', re.I)

def detect_voice_agency(text: str, types: list[str] | None = None) -> list[Violation] | None:
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if not paragraphs:
        paragraphs = [text]
    violations = []
    for para in paragraphs:
        sentences = _split_sentences(para)
        if len(sentences) < 2:
            continue
        passive_count = sum(1 for s in sentences if _PASSIVE_RE.search(s))
        if passive_count / len(sentences) > 0.25:
            violations.append(Violation(
                rule_id="§4",
                rule_title="Voice and Agency",
                severity="warning",
                snippet=para[:120],
            ))
            continue
        # Nominalization density check
        all_words = para.split()
        content = _content_words(para)
        if content:
            nom_count = len(_ABSTRACT_NOUN_RE.findall(para))
            if nom_count / len(content) > 0.20:
                violations.append(Violation(
                    rule_id="§4",
                    rule_title="Voice and Agency",
                    severity="warning",
                    snippet=para[:120],
                ))
    return violations
```

- [ ] **Step 7: Run §1–§4 tests**

```bash
.venv/bin/pytest tests/test_standards.py::TestClarity tests/test_standards.py::TestCohesion tests/test_standards.py::TestConcision tests/test_standards.py::TestVoiceAgency -v
```
Expected: all PASS

- [ ] **Step 8: Run full suite**

```bash
.venv/bin/pytest -q
```
Expected: ~121 passed, 3 skipped

- [ ] **Step 9: Commit**

```bash
git add src/corpus_inference_query/detectors/rules.py tests/test_standards.py
git commit -m "feat(detectors): implement §1–§4 clarity, cohesion, concision, voice/agency"
```

---

## Task 4: §5–§8 Universal Detectors

**Files:**
- Modify: `src/corpus_inference_query/detectors/rules.py`
- Modify: `tests/test_standards.py`

- [ ] **Step 1: Write failing tests for §5–§8**

Add to `tests/test_standards.py`:

```python
from corpus_inference_query.detectors.rules import (
    detect_diction_register,
    detect_sentence_rhythm,
    detect_audience_fit,
    detect_argument_honesty,
)


class TestDictionRegister:
    def test_casual_in_formal_type_flagged(self) -> None:
        text = "The system is gonna be totally awesome once we fix this."
        result = detect_diction_register(text, types=["technical-doc"])
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§5"

    def test_casual_in_informal_type_clean(self) -> None:
        text = "This is gonna be awesome, I promise!"
        assert detect_diction_register(text, types=["blog-post"]) == []

    def test_no_types_no_formal_violation(self) -> None:
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

    def test_fewer_than_three_sentences_skipped(self) -> None:
        assert detect_sentence_rhythm("Hello. World.") == []


class TestAudienceFit:
    def test_complex_email_flagged(self) -> None:
        long_sent = "The multifaceted ramifications of the aforementioned contractual obligations necessitate immediate remediation of the underlying systemic deficiencies."
        result = detect_audience_fit(long_sent, types=["email"])
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§7"

    def test_no_types_skipped(self) -> None:
        result = detect_audience_fit("Some text.", types=None)
        assert result is None

    def test_appropriate_technical_doc_clean(self) -> None:
        text = "The API endpoint accepts POST requests. Authentication uses Bearer tokens. The response contains JSON."
        result = detect_audience_fit(text, types=["technical-doc"])
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
```

- [ ] **Step 2: Run to confirm failures**

```bash
.venv/bin/pytest tests/test_standards.py::TestDictionRegister tests/test_standards.py::TestSentenceRhythm tests/test_standards.py::TestAudienceFit tests/test_standards.py::TestArgumentHonesty -v
```
Expected: FAIL

- [ ] **Step 3: Implement `detect_diction_register`**

```python
_CASUAL_MARKERS = frozenset(['kinda', 'gonna', 'wanna', 'gotta', 'awesome', 'totally', 'literally', 'basically'])
_FORMAL_TYPES = frozenset(['technical-doc', 'rfc', 'white-paper', 'memo', 'letter', 'cover-letter'])

def detect_diction_register(text: str, types: list[str] | None = None) -> list[Violation] | None:
    if not types or not any(t in _FORMAL_TYPES for t in types):
        return []
    words_lower = set(w.lower().strip('.,!?;:()"\'') for w in text.split())
    found = words_lower & _CASUAL_MARKERS
    if not found:
        return []
    return [Violation(
        rule_id="§5",
        rule_title="Diction and Register",
        severity="warning",
        snippet=f"Casual marker(s) in formal context: {', '.join(sorted(found))}",
    )]
```

- [ ] **Step 4: Implement `detect_sentence_rhythm`**

```python
def detect_sentence_rhythm(text: str, types: list[str] | None = None) -> list[Violation] | None:
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()] or [text]
    violations = []
    for para in paragraphs:
        sentences = _split_sentences(para)
        if len(sentences) < 3:
            continue
        lengths = [len(s.split()) for s in sentences]
        try:
            std_dev = statistics.stdev(lengths)
        except statistics.StatisticsError:
            continue
        if std_dev < 3:
            violations.append(Violation(
                rule_id="§6",
                rule_title="Sentence Rhythm",
                severity="info",
                snippet=para[:120],
            ))
    return violations
```

- [ ] **Step 5: Implement `detect_audience_fit`**

```python
_FK_RANGES: dict[str, tuple[float, float]] = {
    "email": (55.0, 85.0),
    "letter": (55.0, 85.0),
    "newsletter": (55.0, 85.0),
    "blog-post": (55.0, 85.0),
    "regular-blog": (55.0, 85.0),
    "technical-doc": (25.0, 60.0),
    "rfc": (25.0, 60.0),
    "readme": (25.0, 60.0),
    "white-paper": (25.0, 60.0),
    "memo": (40.0, 70.0),
    "speech": (65.0, 95.0),
    "talk-transcript": (65.0, 95.0),
    "op-ed": (45.0, 75.0),
    "article": (45.0, 75.0),
    "essay": (40.0, 70.0),
}

def detect_audience_fit(text: str, types: list[str] | None = None) -> list[Violation] | None:
    if not types:
        return None  # skip: type_unknown
    matched = [(t, _FK_RANGES[t]) for t in types if t in _FK_RANGES]
    if not matched:
        return []
    fre = _flesch_reading_ease(text)
    violations = []
    for t, (lo, hi) in matched:
        if not (lo <= fre <= hi):
            violations.append(Violation(
                rule_id="§7",
                rule_title="Audience Fit",
                severity="info",
                snippet=f"Flesch Reading Ease {fre:.1f} (expected {lo:.0f}–{hi:.0f} for type '{t}')",
            ))
    return violations
```

- [ ] **Step 6: Implement `detect_argument_honesty`**

```python
_HEDGE_WORDS = ['seems', 'appears', 'arguably', 'perhaps', 'possibly', 'might', 'could', 'may']
_INTENSIFIER_PATTERNS = [
    re.compile(r'\bobviously\b', re.I),
    re.compile(r'\bclearly\b', re.I),
    re.compile(r'\bcertainly\b', re.I),
    re.compile(r'\beveryone knows\b', re.I),
    re.compile(r'\bit is clear\b', re.I),
    re.compile(r'\bneedless to say\b', re.I),
]

def detect_argument_honesty(text: str, types: list[str] | None = None) -> list[Violation] | None:
    violations = []
    # Hedge cluster: ≥3 hedge words within any 50-word window
    words = text.lower().split()
    for i in range(len(words) - 50):
        window = words[i:i + 50]
        count = sum(1 for w in window if w.strip('.,!?;:"\'') in _HEDGE_WORDS)
        if count >= 3:
            snippet = ' '.join(words[i:i + 12])
            violations.append(Violation(
                rule_id="§8",
                rule_title="Argument Honesty",
                severity="warning",
                snippet=snippet[:120],
            ))
            break  # one violation per text for hedge cluster
    # Bare intensifiers
    for pattern in _INTENSIFIER_PATTERNS:
        for m in pattern.finditer(text):
            violations.append(Violation(
                rule_id="§8",
                rule_title="Argument Honesty",
                severity="warning",
                snippet=f'"{m.group()}" — unsupported intensifier',
                span=(m.start(), m.end()),
            ))
    return violations
```

- [ ] **Step 7: Run §5–§8 tests**

```bash
.venv/bin/pytest tests/test_standards.py::TestDictionRegister tests/test_standards.py::TestSentenceRhythm tests/test_standards.py::TestAudienceFit tests/test_standards.py::TestArgumentHonesty -v
```
Expected: all PASS

- [ ] **Step 8: Full suite**

```bash
.venv/bin/pytest -q
```
Expected: ~132 passed, 3 skipped

- [ ] **Step 9: Commit**

```bash
git add src/corpus_inference_query/detectors/rules.py tests/test_standards.py
git commit -m "feat(detectors): implement §5–§8 diction, rhythm, audience fit, argument honesty"
```

---

## Task 5: §9–§12 Universal Detectors

**Files:**
- Modify: `src/corpus_inference_query/detectors/rules.py`
- Modify: `tests/test_standards.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_standards.py`:

```python
from corpus_inference_query.detectors.rules import (
    detect_opening_craft,
    detect_closing_craft,
    detect_concrete_abstract,
    detect_style_consciousness,
)


class TestOpeningCraft:
    def test_long_first_sentence_flagged(self) -> None:
        long_opener = "This paper will carefully examine and discuss the many important aspects and dimensions of sentence craft and how it applies to the development of an engaging and coherent writing style across multiple genres and contexts."
        result = detect_opening_craft(long_opener)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§9"

    def test_throat_clearing_opener_flagged(self) -> None:
        result = detect_opening_craft("This essay will argue that sentences matter.")
        assert result is not None and len(result) >= 1

    def test_strong_opener_clean(self) -> None:
        assert detect_opening_craft("Sentences make readers.") == []

    def test_question_opener_clean(self) -> None:
        assert detect_opening_craft("What makes a sentence work?") == []

    def test_empty_text_no_error(self) -> None:
        assert detect_opening_craft("") == []


class TestClosingCraft:
    def test_in_conclusion_flagged(self) -> None:
        text = "First sentence here.\n\nIn conclusion, sentences matter to all writers."
        result = detect_closing_craft(text)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§10"

    def test_to_summarize_flagged(self) -> None:
        result = detect_closing_craft("Body text.\n\nTo summarize, this shows the point.")
        assert result is not None and len(result) >= 1

    def test_strong_closer_clean(self) -> None:
        text = "First sentence.\n\nSentences are the writer's only material."
        assert detect_closing_craft(text) == []


class TestConcreteAbstract:
    def test_high_abstract_density_flagged(self) -> None:
        text = "The implementation of organizational transformation requires commitment to the achievement of foundational improvement through the establishment of clear communication."
        result = detect_concrete_abstract(text)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§11"

    def test_concrete_text_clean(self) -> None:
        text = "The team fixed the bug. They shipped the feature on Tuesday."
        assert detect_concrete_abstract(text) == []


class TestStyleConsciousness:
    def test_style_drift_flagged(self) -> None:
        p1 = "And the river rose. And the banks broke. And the town flooded."
        p2 = "Although the waters had receded, since the damage had been done, recovery was slow."
        text = p1 + "\n\n" + p2
        result = detect_style_consciousness(text)
        assert result is not None  # may be [] if paragraphs too short — acceptable
```

- [ ] **Step 2: Run to confirm failures**

```bash
.venv/bin/pytest tests/test_standards.py::TestOpeningCraft tests/test_standards.py::TestClosingCraft tests/test_standards.py::TestConcreteAbstract -v
```
Expected: FAIL

- [ ] **Step 3: Implement `detect_opening_craft`**

```python
_THROAT_CLEARING_RE = re.compile(
    r'^(This|In this|The purpose of|I will|This paper|This essay|In this paper|This article)',
    re.I,
)

def detect_opening_craft(text: str, types: list[str] | None = None) -> list[Violation] | None:
    sentences = _split_sentences(text.strip())
    if not sentences:
        return []
    first = sentences[0]
    violations = []
    if len(first.split()) > 25:
        violations.append(Violation(
            rule_id="§9",
            rule_title="Opening Craft",
            severity="warning",
            snippet=first[:120],
        ))
    if _THROAT_CLEARING_RE.match(first.strip()):
        violations.append(Violation(
            rule_id="§9",
            rule_title="Opening Craft",
            severity="warning",
            snippet=first[:120],
        ))
    return violations
```

- [ ] **Step 4: Implement `detect_closing_craft`**

```python
_SUMMATIVE_CLOSER_RE = re.compile(
    r'^(In conclusion|To summarize|In summary|To conclude|As I have shown|As we have seen|Thus,? it can be seen)',
    re.I,
)

def detect_closing_craft(text: str, types: list[str] | None = None) -> list[Violation] | None:
    sentences = _split_sentences(text.strip())
    if not sentences:
        return []
    last = sentences[-1]
    if _SUMMATIVE_CLOSER_RE.match(last.strip()):
        return [Violation(
            rule_id="§10",
            rule_title="Closing Craft",
            severity="warning",
            snippet=last[:120],
        )]
    return []
```

- [ ] **Step 5: Implement `detect_concrete_abstract`**

```python
_ABSTRACT_NOUN_SUFFIX_RE = re.compile(r'\b\w{5,}(?:tion|ness|ment|ity|ism|ance|ence)\b', re.I)

def detect_concrete_abstract(text: str, types: list[str] | None = None) -> list[Violation] | None:
    content = _content_words(text)
    if not content:
        return []
    abstract_count = len(_ABSTRACT_NOUN_SUFFIX_RE.findall(text))
    if abstract_count / len(content) > 0.25:
        return [Violation(
            rule_id="§11",
            rule_title="Concrete Over Abstract",
            severity="info",
            snippet=f"Abstract noun density: {abstract_count}/{len(content)} content words ({100*abstract_count/len(content):.0f}%)",
        )]
    return []
```

- [ ] **Step 6: Implement `detect_style_consciousness`**

```python
_ADDITIVE_RE = re.compile(r'^(And|But|Or|Yet|So)\b', re.I)
_SUBORDINATING_RE = re.compile(r'^(Although|Because|Since|While|Unless|If|When|Before|After|Though)\b', re.I)

def detect_style_consciousness(text: str, types: list[str] | None = None) -> list[Violation] | None:
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) < 2:
        return []
    violations = []
    styles: list[str] = []
    for para in paragraphs:
        sentences = _split_sentences(para)
        additive = sum(1 for s in sentences if _ADDITIVE_RE.match(s.strip()))
        subordinating = sum(1 for s in sentences if _SUBORDINATING_RE.match(s.strip()))
        if additive >= 3:
            styles.append('additive')
        elif subordinating >= 3:
            styles.append('subordinating')
        else:
            styles.append('mixed')
    for i in range(1, len(styles)):
        if styles[i - 1] != styles[i] and styles[i - 1] != 'mixed' and styles[i] != 'mixed':
            violations.append(Violation(
                rule_id="§12",
                rule_title="Style Consciousness",
                severity="info",
                snippet=f"Style shift: paragraph {i} is {styles[i-1]}, paragraph {i+1} is {styles[i]}",
            ))
    return violations
```

- [ ] **Step 7: Run §9–§12 tests**

```bash
.venv/bin/pytest tests/test_standards.py::TestOpeningCraft tests/test_standards.py::TestClosingCraft tests/test_standards.py::TestConcreteAbstract tests/test_standards.py::TestStyleConsciousness -v
```
Expected: all PASS

- [ ] **Step 8: Full suite**

```bash
.venv/bin/pytest -q
```
Expected: ~143 passed, 3 skipped

- [ ] **Step 9: Commit**

```bash
git add src/corpus_inference_query/detectors/rules.py tests/test_standards.py
git commit -m "feat(detectors): implement §9–§12 opening, closing, concrete/abstract, style consciousness"
```

---

## Task 6: §13–§15 Universal Detectors

**Files:**
- Modify: `src/corpus_inference_query/detectors/rules.py`
- Modify: `tests/test_standards.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_standards.py`:

```python
from corpus_inference_query.detectors.rules import (
    detect_voice_fidelity,
    detect_transitions,
    detect_lede_and_title,
)


class TestVoiceFidelity:
    def test_always_skipped_in_m3(self) -> None:
        result = detect_voice_fidelity("Any text at all.")
        assert result is None

    def test_skip_with_types(self) -> None:
        result = detect_voice_fidelity("Text.", types=["essay"])
        assert result is None


class TestTransitions:
    def test_three_disconnected_paragraphs_flagged(self) -> None:
        text = (
            "Dogs are loyal animals. They make great pets.\n\n"
            "The history of Rome spans centuries. The empire fell.\n\n"
            "Quantum computing is advancing rapidly. New chips appear daily."
        )
        result = detect_transitions(text)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§14"

    def test_paragraphs_with_transitions_clean(self) -> None:
        text = (
            "Dogs are loyal animals. They make great pets.\n\n"
            "However, not all dogs are well-suited for apartment living.\n\n"
            "Therefore, prospective owners should consider their space carefully."
        )
        assert detect_transitions(text) == []

    def test_single_paragraph_clean(self) -> None:
        assert detect_transitions("One paragraph only.") == []


class TestLedeAndTitle:
    def test_long_title_flagged(self) -> None:
        text = "A Comprehensive Survey of the Current State of Sentence-Level Writing Craft Research\n\nBody text here."
        result = detect_lede_and_title(text)
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§15"

    def test_short_title_clean(self) -> None:
        text = "The Science of the Sentence\n\nBody text here."
        assert detect_lede_and_title(text) == []

    def test_no_nut_graf_in_article_flagged(self) -> None:
        text = "Opening line.\n\nSecond paragraph with no stakes language.\n\nThird paragraph continues."
        result = detect_lede_and_title(text, types=["article"])
        assert result is not None and len(result) >= 1

    def test_nut_graf_present_clean(self) -> None:
        text = "Opening line.\n\nThis matters because the impact on readers is significant.\n\nMore text."
        assert detect_lede_and_title(text, types=["article"]) == []
```

- [ ] **Step 2: Run to confirm failures (§14 and §15 stubs)**

```bash
.venv/bin/pytest tests/test_standards.py::TestVoiceFidelity tests/test_standards.py::TestTransitions tests/test_standards.py::TestLedeAndTitle -v
```
Expected: §13 PASS (already returns None), §14 and §15 FAIL

- [ ] **Step 3: Implement `detect_transitions`**

```python
_TRANSITION_WORDS = frozenset([
    'however', 'therefore', 'furthermore', 'moreover', 'additionally',
    'consequently', 'nevertheless', 'thus', 'hence', 'meanwhile',
    'subsequently', 'conversely', 'specifically', 'for example',
    'in contrast', 'on the other hand', 'that said', 'in other words',
    'as a result', 'even so', 'nonetheless',
])

def detect_transitions(text: str, types: list[str] | None = None) -> list[Violation] | None:
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) < 3:
        return []
    # Check for 3+ consecutive paragraphs with no transition word at start
    no_transition_streak = 0
    violations = []
    for para in paragraphs:
        first_words = set(para.lower().split()[:6])
        has_transition = bool(first_words & _TRANSITION_WORDS) or any(
            phrase in para[:60].lower() for phrase in ['for example', 'in contrast', 'on the other hand', 'that said', 'in other words', 'as a result']
        )
        if has_transition:
            no_transition_streak = 0
        else:
            no_transition_streak += 1
        if no_transition_streak >= 3:
            violations.append(Violation(
                rule_id="§14",
                rule_title="Transitions",
                severity="info",
                snippet=para[:120],
            ))
            no_transition_streak = 0  # reset to avoid cascading violations
    return violations
```

- [ ] **Step 4: Implement `detect_lede_and_title`**

```python
_NUT_GRAF_WORDS = frozenset(['why', 'matters', 'means', 'impact', 'effect', 'result', 'important', 'significant', 'reveals', 'shows', 'found'])

def detect_lede_and_title(text: str, types: list[str] | None = None) -> list[Violation] | None:
    lines = text.split('\n')
    violations = []
    # Title check: if first non-empty line is ≤120 chars and followed by blank, treat as title
    first_line = next((l.strip() for l in lines if l.strip()), '')
    if first_line and len(first_line) <= 120 and len(lines) > 1 and not lines[1].strip():
        if len(first_line.split()) > 15:
            violations.append(Violation(
                rule_id="§15",
                rule_title="Lede and Title Craft",
                severity="warning",
                snippet=f'Title too long ({len(first_line.split())} words): "{first_line[:80]}"',
            ))
    # Nut graf check (article type only)
    if types and 'article' in types:
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        first_three = ' '.join(paragraphs[:3]).lower()
        if not any(w in first_three for w in _NUT_GRAF_WORDS):
            violations.append(Violation(
                rule_id="§15",
                rule_title="Lede and Title Craft",
                severity="info",
                snippet="No nut graf found in first 3 paragraphs (missing stakes language)",
            ))
    return violations
```

- [ ] **Step 5: Run §13–§15 tests**

```bash
.venv/bin/pytest tests/test_standards.py::TestVoiceFidelity tests/test_standards.py::TestTransitions tests/test_standards.py::TestLedeAndTitle -v
```
Expected: all PASS

- [ ] **Step 6: Full suite**

```bash
.venv/bin/pytest -q
```
Expected: ~154 passed, 3 skipped

- [ ] **Step 7: Commit**

```bash
git add src/corpus_inference_query/detectors/rules.py tests/test_standards.py
git commit -m "feat(detectors): implement §13–§15 voice fidelity (skip), transitions, lede/title"
```

---

## Task 7: §A–§E Type Addenda

**Files:**
- Modify: `src/corpus_inference_query/detectors/rules.py`
- Modify: `tests/test_standards.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_standards.py`:

```python
from corpus_inference_query.detectors.rules import (
    detect_article,
    detect_email,
    detect_letter,
    detect_technical_doc,
    detect_newsletter,
)


class TestArticle:
    def test_unsourced_quotes_flagged(self) -> None:
        text = 'The president said "this is great" and everyone applauded without any attribution.'
        result = detect_article(text, types=["article"])
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§A"

    def test_sourced_quote_clean(self) -> None:
        text = 'According to the president, "this is great."'
        assert detect_article(text, types=["article"]) == []

    def test_too_short_flagged(self) -> None:
        result = detect_article("Short.", types=["article"])
        assert result is not None and len(result) >= 1


class TestEmail:
    def test_too_many_paragraphs_flagged(self) -> None:
        text = "\n\n".join(["Para " + str(i) for i in range(5)])
        result = detect_email(text, types=["email"])
        assert result is not None and len(result) >= 1
        assert any(v.rule_id == "§B" for v in result)

    def test_no_explicit_ask_flagged(self) -> None:
        text = "Hi there.\n\nJust wanted to share some thoughts on the project. Everything seems fine."
        result = detect_email(text, types=["email"])
        assert result is not None and len(result) >= 1

    def test_clear_email_clean(self) -> None:
        text = "Hi.\n\nCould you review this by Friday?\n\nThanks, let me know."
        assert detect_email(text, types=["email"]) == []


class TestLetter:
    def test_missing_salutation_flagged(self) -> None:
        text = "I hope this letter finds you well. Regards, Amos."
        result = detect_letter(text, types=["letter"])
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§C"

    def test_missing_signoff_flagged(self) -> None:
        text = "Dear John,\n\nI hope this letter finds you well."
        result = detect_letter(text, types=["letter"])
        assert result is not None and len(result) >= 1

    def test_complete_letter_clean(self) -> None:
        text = "Dear John,\n\nI hope this letter finds you well.\n\nSincerely, Amos"
        assert detect_letter(text, types=["letter"]) == []


class TestTechnicalDoc:
    def test_no_sections_in_long_doc_flagged(self) -> None:
        long_text = " ".join(["word"] * 600)  # 600-word block, no headings
        result = detect_technical_doc(long_text, types=["technical-doc"])
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§D"

    def test_doc_with_sections_clean(self) -> None:
        text = "Introduction\n\n" + " ".join(["word"] * 200) + "\n\n## 1. Overview\n\n" + " ".join(["word"] * 200)
        assert detect_technical_doc(text, types=["technical-doc"]) == []


class TestNewsletter:
    def test_no_cta_flagged(self) -> None:
        text = "Welcome to the newsletter!\n\nHere is the content for this week.\n\nThank you for reading."
        result = detect_newsletter(text, types=["newsletter"])
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§E"

    def test_newsletter_with_cta_clean(self) -> None:
        text = "Welcome!\n\nContent here.\n\nForward this to a friend or subscribe for more."
        assert detect_newsletter(text, types=["newsletter"]) == []
```

- [ ] **Step 2: Run to confirm failures**

```bash
.venv/bin/pytest tests/test_standards.py::TestArticle tests/test_standards.py::TestEmail tests/test_standards.py::TestLetter tests/test_standards.py::TestTechnicalDoc tests/test_standards.py::TestNewsletter -v
```
Expected: FAIL

- [ ] **Step 3: Implement `detect_article`**

```python
_QUOTE_RE = re.compile(r'"([^"]{5,})"')
_ATTRIBUTION_RE = re.compile(r'\b(said|according to|wrote|noted|reported|stated|explained|added)\b', re.I)

def detect_article(text: str, types: list[str] | None = None) -> list[Violation] | None:
    violations = []
    words = text.split()
    if len(words) < 400:
        violations.append(Violation(rule_id="§A", rule_title="Article", severity="info",
                                     snippet=f"Article is only {len(words)} words (minimum 400 recommended)"))
    if len(words) > 5000:
        violations.append(Violation(rule_id="§A", rule_title="Article", severity="info",
                                     snippet=f"Article is {len(words)} words (maximum 5000 recommended)"))
    for m in _QUOTE_RE.finditer(text):
        surrounding = text[max(0, m.start() - 50):m.end() + 50]
        if not _ATTRIBUTION_RE.search(surrounding):
            violations.append(Violation(rule_id="§A", rule_title="Article", severity="warning",
                                         snippet=f'Unattributed quote: "{m.group(1)[:60]}"',
                                         span=(m.start(), m.end())))
    return violations
```

- [ ] **Step 4: Implement `detect_email`**

```python
_IMPERATIVE_ASK_RE = re.compile(
    r'\b(please|could you|can you|i need|let me know|would you|are you able)\b',
    re.I,
)

def detect_email(text: str, types: list[str] | None = None) -> list[Violation] | None:
    violations = []
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) > 3:
        violations.append(Violation(rule_id="§B", rule_title="Email", severity="warning",
                                     snippet=f"Email has {len(paragraphs)} paragraphs (max 3 recommended)"))
    # Check for explicit ask in first 2 sentences
    first_two_sents = ' '.join(_split_sentences(text)[:2])
    if not _IMPERATIVE_ASK_RE.search(first_two_sents) and '?' not in first_two_sents:
        violations.append(Violation(rule_id="§B", rule_title="Email", severity="info",
                                     snippet="No explicit ask in first two sentences"))
    return violations
```

- [ ] **Step 5: Implement `detect_letter`**

```python
_SALUTATION_RE = re.compile(r'^dear\b', re.I | re.M)
_SIGNOFF_RE = re.compile(r'\b(sincerely|best regards|respectfully|yours|regards|warm regards|kind regards|with appreciation)\b', re.I)

def detect_letter(text: str, types: list[str] | None = None) -> list[Violation] | None:
    violations = []
    if not _SALUTATION_RE.search(text):
        violations.append(Violation(rule_id="§C", rule_title="Letter", severity="warning",
                                     snippet="Missing salutation (expected 'Dear ...')"))
    if not _SIGNOFF_RE.search(text):
        violations.append(Violation(rule_id="§C", rule_title="Letter", severity="warning",
                                     snippet="Missing sign-off (e.g., 'Sincerely', 'Best regards')"))
    return violations
```

- [ ] **Step 6: Implement `detect_technical_doc`**

```python
_HEADING_RE = re.compile(r'(^#{1,3}\s+\S|^\d+\.\s+\S)', re.M)

def detect_technical_doc(text: str, types: list[str] | None = None) -> list[Violation] | None:
    violations = []
    words = text.split()
    if len(words) >= 500 and not _HEADING_RE.search(text):
        violations.append(Violation(rule_id="§D", rule_title="Technical Doc", severity="warning",
                                     snippet=f"Doc has {len(words)} words but no headings or numbered sections"))
    # Context-first: flag if text opens with code block
    if text.lstrip().startswith('```') or text.lstrip().startswith('$'):
        violations.append(Violation(rule_id="§D", rule_title="Technical Doc", severity="info",
                                     snippet="Doc opens with code/command rather than context paragraph"))
    return violations
```

- [ ] **Step 7: Implement `detect_newsletter`**

```python
_CTA_RE = re.compile(r'\b(subscribe|unsubscribe|forward this|sign up|opt out)\b', re.I)

def detect_newsletter(text: str, types: list[str] | None = None) -> list[Violation] | None:
    violations = []
    if not _CTA_RE.search(text):
        violations.append(Violation(rule_id="§E", rule_title="Newsletter", severity="info",
                                     snippet="No subscribe/unsubscribe or forward CTA found"))
    section_count = len(re.findall(r'^#{1,3}\s', text, re.M))
    if section_count > 3:
        violations.append(Violation(rule_id="§E", rule_title="Newsletter", severity="info",
                                     snippet=f"Newsletter has {section_count} sections (single main topic recommended)"))
    return violations
```

- [ ] **Step 8: Run §A–§E tests**

```bash
.venv/bin/pytest tests/test_standards.py::TestArticle tests/test_standards.py::TestEmail tests/test_standards.py::TestLetter tests/test_standards.py::TestTechnicalDoc tests/test_standards.py::TestNewsletter -v
```
Expected: all PASS

- [ ] **Step 9: Full suite**

```bash
.venv/bin/pytest -q
```
Expected: ~169 passed, 3 skipped

- [ ] **Step 10: Commit**

```bash
git add src/corpus_inference_query/detectors/rules.py tests/test_standards.py
git commit -m "feat(detectors): implement §A–§E article, email, letter, technical-doc, newsletter"
```

---

## Task 8: §F–§J Type Addenda

**Files:**
- Modify: `src/corpus_inference_query/detectors/rules.py`
- Modify: `tests/test_standards.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_standards.py`:

```python
from corpus_inference_query.detectors.rules import (
    detect_op_ed,
    detect_blog_post,
    detect_white_paper,
    detect_memo,
    detect_speech,
)


class TestOpEd:
    def test_no_claim_in_first_paragraph_flagged(self) -> None:
        text = "The weather was nice today.\n\nMany people went outside. They enjoyed themselves."
        result = detect_op_ed(text, types=["op-ed"])
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§F"

    def test_claim_present_clean(self) -> None:
        text = "Congress should abolish the electoral college.\n\nHere is why this matters."
        assert detect_op_ed(text, types=["op-ed"]) == []

    def test_too_long_flagged(self) -> None:
        text = " ".join(["word"] * 1300)
        result = detect_op_ed(text, types=["op-ed"])
        assert result is not None and len(result) >= 1


class TestBlogPost:
    def test_long_post_no_subheads_flagged(self) -> None:
        text = " ".join(["word"] * 500)
        result = detect_blog_post(text, types=["blog-post"])
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§G"

    def test_post_with_subheads_clean(self) -> None:
        text = " ".join(["word"] * 200) + "\n\n## Section\n\n" + " ".join(["word"] * 200)
        assert detect_blog_post(text, types=["blog-post"]) == []

    def test_short_post_no_subhead_needed(self) -> None:
        text = "This is a short post. It does not need subheads."
        assert detect_blog_post(text, types=["blog-post"]) == []


class TestWhitePaper:
    def test_no_executive_summary_flagged(self) -> None:
        text = " ".join(["word"] * 800)
        result = detect_white_paper(text, types=["white-paper"])
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§H"

    def test_white_paper_with_summary_clean(self) -> None:
        text = "Executive Summary\n\nThis paper recommends adoption of the policy.\n\n" + " ".join(["word"] * 200)
        assert detect_white_paper(text, types=["white-paper"]) == []


class TestMemo:
    def test_no_header_flagged(self) -> None:
        text = "Just a regular paragraph without memo headers."
        result = detect_memo(text, types=["memo"])
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§I"

    def test_valid_memo_clean(self) -> None:
        text = "TO: Team\nFROM: Manager\nRE: Project Update\n\nThe project is on track. See bullets below.\n\n- Item one\n- Item two"
        assert detect_memo(text, types=["memo"]) == []


class TestSpeech:
    def test_long_sentences_flagged(self) -> None:
        text = " ".join([
            "The fundamental transformation of our understanding of civic responsibility requires an unprecedented commitment to democratic participation and the sustained engagement of every member of our diverse and multifaceted community.",
            "We must work harder together."
        ])
        result = detect_speech(text, types=["speech"])
        assert result is not None and len(result) >= 1
        assert result[0].rule_id == "§J"

    def test_short_sentences_clean(self) -> None:
        text = "We can do this. You know it. I know it. Let us begin. Together we rise. Now is the time."
        assert detect_speech(text, types=["speech"]) == []

    def test_no_audience_address_flagged(self) -> None:
        text = "The proposal has three components. The first is budget. The second is timeline. The third is scope."
        result = detect_speech(text, types=["speech"])
        assert result is not None and len(result) >= 1
```

- [ ] **Step 2: Run to confirm failures**

```bash
.venv/bin/pytest tests/test_standards.py::TestOpEd tests/test_standards.py::TestBlogPost tests/test_standards.py::TestWhitePaper tests/test_standards.py::TestMemo tests/test_standards.py::TestSpeech -v
```
Expected: FAIL

- [ ] **Step 3: Implement `detect_op_ed`**

```python
_CLAIM_VERB_RE = re.compile(r'\b(should|must|is wrong|is right|needs to|ought to|demands|requires|fails|succeeds)\b', re.I)

def detect_op_ed(text: str, types: list[str] | None = None) -> list[Violation] | None:
    violations = []
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    first_para = paragraphs[0] if paragraphs else text
    if not _CLAIM_VERB_RE.search(first_para):
        violations.append(Violation(rule_id="§F", rule_title="Op-Ed", severity="warning",
                                     snippet="First paragraph lacks a clear claim verb (should/must/needs to/etc.)"))
    words = text.split()
    if len(words) > 1200:
        violations.append(Violation(rule_id="§F", rule_title="Op-Ed", severity="warning",
                                     snippet=f"Op-ed is {len(words)} words (max 1200 recommended)"))
    return violations
```

- [ ] **Step 4: Implement `detect_blog_post`**

```python
def detect_blog_post(text: str, types: list[str] | None = None) -> list[Violation] | None:
    violations = []
    words = text.split()
    if len(words) <= 300:
        return []
    word_count = len(words)
    heading_count = len(re.findall(r'^#{1,3}\s', text, re.M))
    expected_headings = max(1, word_count // 400)
    if heading_count < expected_headings:
        violations.append(Violation(rule_id="§G", rule_title="Blog Post", severity="info",
                                     snippet=f"{word_count}-word post has {heading_count} subheads (expected ≥{expected_headings})"))
    return violations
```

- [ ] **Step 5: Implement `detect_white_paper`**

```python
_EXEC_SUMMARY_RE = re.compile(r'\b(executive summary|abstract)\b', re.I)
_RECOMMENDATION_RE = re.compile(r'\b(recommend|we propose|our recommendation|proposed solution)\b', re.I)

def detect_white_paper(text: str, types: list[str] | None = None) -> list[Violation] | None:
    violations = []
    if not _EXEC_SUMMARY_RE.search(text[:200]):
        violations.append(Violation(rule_id="§H", rule_title="White Paper", severity="warning",
                                     snippet="No 'Executive Summary' or 'Abstract' in opening"))
    words = text.split()
    if len(words) >= 800 and not _RECOMMENDATION_RE.search(text):
        violations.append(Violation(rule_id="§H", rule_title="White Paper", severity="info",
                                     snippet="Long white paper lacks a recommendation section"))
    return violations
```

- [ ] **Step 6: Implement `detect_memo`**

```python
_MEMO_HEADER_RE = re.compile(r'\bTO:\s*\S', re.I | re.M)
_MEMO_FROM_RE = re.compile(r'\bFROM:\s*\S', re.I | re.M)
_MEMO_RE_RE = re.compile(r'\b(RE:|SUBJECT:)\s*\S', re.I | re.M)
_BULLET_RE = re.compile(r'^[-*•]|\d+\.', re.M)

def detect_memo(text: str, types: list[str] | None = None) -> list[Violation] | None:
    violations = []
    header_ok = _MEMO_HEADER_RE.search(text) and _MEMO_FROM_RE.search(text) and _MEMO_RE_RE.search(text)
    if not header_ok:
        violations.append(Violation(rule_id="§I", rule_title="Memo", severity="warning",
                                     snippet="Memo missing TO:/FROM:/RE: header block"))
    if not _BULLET_RE.search(text):
        violations.append(Violation(rule_id="§I", rule_title="Memo", severity="info",
                                     snippet="Memo has no bullet or numbered list (BLUF support expected)"))
    words = text.split()
    if len(words) > 1800:
        violations.append(Violation(rule_id="§I", rule_title="Memo", severity="info",
                                     snippet=f"Memo is {len(words)} words (max ~1800/4 pages recommended)"))
    return violations
```

- [ ] **Step 7: Implement `detect_speech`**

```python
_AUDIENCE_ADDRESS_RE = re.compile(r'\b(you|your|we|our|us)\b', re.I)
_TRICOLON_RE = re.compile(r'(?:\b\w[\w\s]{2,20},\s+){2}\w[\w\s]{2,20}\b')

def detect_speech(text: str, types: list[str] | None = None) -> list[Violation] | None:
    violations = []
    sentences = _split_sentences(text)
    if not sentences:
        return []
    lengths = [len(s.split()) for s in sentences]
    try:
        median_len = statistics.median(lengths)
    except statistics.StatisticsError:
        median_len = 0
    if median_len > 18:
        violations.append(Violation(rule_id="§J", rule_title="Speech", severity="warning",
                                     snippet=f"Median sentence length {median_len:.0f} words (target ≤18 for oral delivery)"))
    if not _AUDIENCE_ADDRESS_RE.search(text):
        violations.append(Violation(rule_id="§J", rule_title="Speech", severity="warning",
                                     snippet="No direct audience address (you/we/our) found"))
    return violations
```

- [ ] **Step 8: Run §F–§J tests**

```bash
.venv/bin/pytest tests/test_standards.py::TestOpEd tests/test_standards.py::TestBlogPost tests/test_standards.py::TestWhitePaper tests/test_standards.py::TestMemo tests/test_standards.py::TestSpeech -v
```
Expected: all PASS

- [ ] **Step 9: Full suite**

```bash
.venv/bin/pytest -q
```
Expected: ~186 passed, 3 skipped

- [ ] **Step 10: Commit**

```bash
git add src/corpus_inference_query/detectors/rules.py tests/test_standards.py
git commit -m "feat(detectors): implement §F–§J op-ed, blog, white-paper, memo, speech"
```

---

## Task 9: Wire Detectors into Repository + Update Tool Response

**Files:**
- Modify: `src/corpus_inference_query/corpus_repository.py` (replace stub)
- Modify: `src/corpus_inference_query/tool_responses.py` (replace `format_check_stub` → `format_check_results`)
- Modify: `src/corpus_inference_query/server.py` (update `check_against_standards` tool call)
- Modify: `tests/test_tool_responses.py` (update formatter tests)
- Modify: `tests/test_server.py` (update integration + mock expectations)

- [ ] **Step 1: Write failing test for the wired repository**

Add to `tests/test_standards.py`:

```python
from pathlib import Path
from corpus_inference_query.corpus_repository import CorpusRepository

_FIXTURE_CORPUS = Path(__file__).parent / "fixtures" / "corpus"


class TestCheckAgainstStandardsIntegration:
    def test_returns_violations_and_skipped(self) -> None:
        repo = CorpusRepository(_FIXTURE_CORPUS)
        result = repo.check_against_standards("Due to the fact that the report was late, we met.")
        assert "violations" in result
        assert "skipped_rules" in result
        assert any(v["rule_id"] == "§3" for v in result["violations"])

    def test_type_addendum_applied(self) -> None:
        repo = CorpusRepository(_FIXTURE_CORPUS)
        result = repo.check_against_standards(
            "Hi.\n\nJust writing to say hello. Nothing specific to ask.",
            types=["email"],
        )
        assert any(v["rule_id"] == "§B" for v in result["violations"])

    def test_voice_fidelity_skipped(self) -> None:
        repo = CorpusRepository(_FIXTURE_CORPUS)
        result = repo.check_against_standards("Any text.")
        skipped_ids = {s["rule_id"] for s in result["skipped_rules"]}
        assert "§13" in skipped_ids
```

- [ ] **Step 2: Run to confirm failures**

```bash
.venv/bin/pytest tests/test_standards.py::TestCheckAgainstStandardsIntegration -v
```
Expected: FAIL — `check_against_standards` still returns stub dict

- [ ] **Step 3: Replace stub in `corpus_repository.py`**

Find and replace the `check_against_standards` method (currently at the bottom of the class):

```python
def check_against_standards(
    self, text: str, types: list[str] | None = None
) -> dict[str, Any]:
    """Run all applicable detectors against text."""
    from .detectors.registry import run_all
    return run_all(text, types)
```

- [ ] **Step 4: Update `tool_responses.py` — replace `format_check_stub` with `format_check_results`**

Remove `format_check_stub` and replace with:

```python
def format_check_results(result: dict[str, Any]) -> str:
    """Format check_against_standards result as readable text."""
    violations = result.get("violations", [])
    skipped = result.get("skipped_rules", [])
    types_used = result.get("types_used", [])

    if not violations and not skipped:
        return "No violations found."

    lines: list[str] = []
    if types_used:
        lines.append(f"**Types checked:** {', '.join(types_used)}")

    if violations:
        lines.append(f"\n**Violations ({len(violations)}):**")
        for v in violations:
            severity_tag = f"[{v['severity'].upper()}]"
            lines.append(f"- {severity_tag} **{v['rule_id']} {v['rule_title']}**: {v['snippet']}")
    else:
        lines.append("\n**No violations found.**")

    if skipped:
        lines.append(f"\n**Skipped rules ({len(skipped)}):** " + ", ".join(
            f"{s['rule_id']} ({s['reason']})" for s in skipped
        ))

    return "\n".join(lines)
```

- [ ] **Step 5: Update `server.py` — replace `format_check_stub` call**

In `server.py`, find `format_check_stub` and update:

```python
from .tool_responses import format_check_results, format_list_corpora, format_reload
```

In the `check_against_standards` tool body, change:
```python
    return format_check_results(_get_repo().check_against_standards(text, types))
```

- [ ] **Step 6: Update `tests/test_tool_responses.py`**

Remove the `TestFormatCheckStub` class and replace with:

```python
from corpus_inference_query.tool_responses import format_check_results


class TestFormatCheckResults:
    def test_no_violations(self) -> None:
        result = {"violations": [], "skipped_rules": [], "types_used": []}
        assert format_check_results(result) == "No violations found."

    def test_violations_rendered(self) -> None:
        result = {
            "violations": [
                {"rule_id": "§3", "rule_title": "Concision", "severity": "warning",
                 "snippet": '"due to the fact that" → "because"', "span": None,
                 "exemplar_citation": None, "suggested_rewrite_from_exemplar": None},
            ],
            "skipped_rules": [],
            "types_used": [],
        }
        formatted = format_check_results(result)
        assert "§3" in formatted
        assert "Concision" in formatted
        assert "WARNING" in formatted

    def test_skipped_rules_listed(self) -> None:
        result = {
            "violations": [],
            "skipped_rules": [{"rule_id": "§13", "rule_title": "Voice Fidelity", "reason": "personal_corpus_empty"}],
            "types_used": [],
        }
        formatted = format_check_results(result)
        assert "§13" in formatted
        assert "personal_corpus_empty" in formatted

    def test_types_used_shown(self) -> None:
        result = {"violations": [], "skipped_rules": [], "types_used": ["email"]}
        assert "email" in format_check_results(result)
```

- [ ] **Step 7: Update `tests/test_server.py`** — find and update `check_against_standards` mock expectations

In `test_server.py`, find the mock setup for `check_against_standards`. The mock `check_against_standards` now returns the new dict format `{violations, skipped_rules, types_used}`. Update the mock:

```python
mock_repo.check_against_standards.return_value = {
    "violations": [],
    "skipped_rules": [{"rule_id": "§13", "rule_title": "Voice Fidelity", "reason": "personal_corpus_empty"}],
    "types_used": [],
}
```

Also update the integration test `test_check_against_standards_contains_not_yet_implemented` — rename it and update the assertion:

```python
def test_check_against_standards_returns_string(self):
    result = check_against_standards("Some text with due to the fact that it matters.")
    assert isinstance(result, str)
    assert len(result) > 0
```

- [ ] **Step 8: Run full suite**

```bash
.venv/bin/pytest -q
```
Expected: ~192 passed, 3 skipped (all green)

- [ ] **Step 9: Commit**

```bash
git add src/corpus_inference_query/corpus_repository.py \
        src/corpus_inference_query/tool_responses.py \
        src/corpus_inference_query/server.py \
        tests/test_tool_responses.py \
        tests/test_server.py \
        tests/test_standards.py
git commit -m "feat(m3): wire detectors into repository; format_check_results replaces stub"
```

- [ ] **Step 10: Tag M3**

```bash
git tag m3-writing-standards
```

---

## Self-Review Checklist

**Spec coverage:**
- §1–§15 universal detectors: Tasks 3–6 ✓
- §A–§J type addenda: Tasks 7–8 ✓
- `standards/writing-standards.md`: Task 1 ✓
- `detectors/` package: Task 2 ✓
- `check_against_standards` wired: Task 9 ✓
- `format_check_results`: Task 9 ✓
- `skipped_rules` array with reason codes: registry.py (§7 type_unknown, §13 personal_corpus_empty) ✓
- Tests: one positive + one negative per detector ✓

**Placeholder scan:** No TBDs. All code blocks are complete.

**Type consistency:**
- `Violation` dataclass defined in Task 2 used consistently in Tasks 3–8
- `run_all()` returns `{violations, skipped_rules, types_used}` — same shape consumed in Task 9
- `format_check_results(result: dict)` takes exactly what `run_all()` returns ✓
- `detect_*` functions all have signature `(text: str, types: list[str] | None) -> list[Violation] | None` ✓

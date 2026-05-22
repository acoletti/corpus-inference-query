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
| A.1 Nut graf | First 3 paragraphs contain stakes language (see §15 detector) |
| A.2 Sourced quotes | Quoted text has attribution within 20 words (`said`, `according to`, `wrote`, `noted`, `reported`) |
| A.3 Word count | 400–5000 words; flag if shorter or longer |
| A.4 Lead type | First paragraph ≤3 sentences |

---

### §B Email

Types: `email`

| Rule | Detector |
|------|----------|
| B.1 Length | ≤3 paragraphs (flag if more) |
| B.2 Explicit ask | First 2 sentences contain `?` or an imperative verb (`Please`, `Could you`, `Can you`, `I need`, `Let me know`) |
| B.3 Subject line | If text opens with `Subject:`, flag subject >12 words |
| B.4 Closing action | Final sentence contains action language |

---

### §C Letter

Types: `letter`, `cover-letter`

| Rule | Detector |
|------|----------|
| C.1 Salutation | Text contains `Dear` within first 3 lines |
| C.2 Sign-off | Text ends with closing phrase (`Sincerely`, `Best regards`, `Respectfully`, `Yours`) |
| C.3 Single occasion | Flag if text contains more than 2 distinct topic-shift markers |

---

### §D Technical Doc / RFC

Types: `technical-doc`, `rfc`, `readme`, `runbook`, `api-doc`

| Rule | Detector |
|------|----------|
| D.1 Context first | First paragraph does not start with code/command |
| D.2 Numbered sections | Flag if text is >500 words and contains no numbered headings |
| D.3 Alternatives | Text ≥800 words contains alternatives language |
| D.4 Terminology | Flag all-caps terms never followed by definition |

---

### §E Newsletter

Types: `newsletter`

| Rule | Detector |
|------|----------|
| E.1 CTA/subscribe | Text contains `subscribe`, `unsubscribe`, or `forward this` |
| E.2 Single thread | Flag if more than 3 `##` section headings |
| E.3 Voice continuity | Opening and closing share register |

---

### §F Op-ed

Types: `op-ed`

| Rule | Detector |
|------|----------|
| F.1 Claim in first paragraph | First paragraph contains a claim verb (`should`, `must`, `needs to`, etc.) |
| F.2 Stakes | First 3 paragraphs contain stakes language |
| F.3 Word count | 600–1200 words |
| F.4 Credibility hook | First 5 sentences contain `I`, `we`, `my`, or `our` |

---

### §G Blog Post

Types: `blog-post`, `regular-blog`

| Rule | Detector |
|------|----------|
| G.1 Subheads | For posts >300 words: at least one `##` heading per 400 words |
| G.2 Register | At least one sentence with conversational markers |
| G.3 Link citation | For posts >500 words: at least one hyperlink |

---

### §H White Paper

Types: `white-paper`

| Rule | Detector |
|------|----------|
| H.1 Executive summary | Text contains `executive summary` or `abstract` within first 200 chars |
| H.2 Numbered sections | Text ≥1000 words has numbered headings |
| H.3 Recommendation | Text contains recommendation language |
| H.4 Citations | Text ≥800 words has at least one citation marker |

---

### §I Memo

Types: `memo`

| Rule | Detector |
|------|----------|
| I.1 Header | Text contains `TO:` and `FROM:` and `RE:` within first 5 lines |
| I.2 BLUF | First sentence after header is declarative |
| I.3 Bullets | Contains at least one list marker |
| I.4 Length | ≤1800 words |

---

### §J Speech / Talk

Types: `speech`, `talk-transcript`

| Rule | Detector |
|------|----------|
| J.1 Short sentences | Median sentence length ≤18 words |
| J.2 Audience address | Contains `you`, `we`, `our`, `your` |
| J.3 Tricolon | Contains at least one tricolon pattern |
| J.4 Sentence variety | At least 20% of sentences ≤8 words |

---

## Annex X — Shorthand-table conventions

When adding a new corpus source:
1. Choose a unique shorthand (2–8 uppercase letters or title abbreviation)
2. Add `[[source]]` block to `writing-corpus/corpus.toml`
3. Assign `default_style` from: `subordinating`, `additive`, `satiric`, `first-sentence`, `last-sentence`, `self-reflexive`, `balanced`, `periodic`
4. Assign `default_type` from the full type list in the design spec §3.4
5. Per-section overrides go in YAML/TOML frontmatter at the top of section files

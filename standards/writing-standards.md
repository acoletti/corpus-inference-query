# Writing Standards

This document defines the rules `check_against_standards` enforces. Each rule
has a mechanical detector — a small Python heuristic in
`src/corpus_inference_query/detectors/rules.py`, registered by id in
`detectors/registry.py`. Detection is **mechanical only**: no LLM calls, no
subjective judgment at runtime. Where a rule's underlying idea (cohesion,
argument honesty, style drift) resists exact measurement, the v1 detector
checks the closest countable proxy and is deliberately conservative — it flags
clear cases and stays quiet on ambiguous ones. Thresholds are a starting point,
not a final calibration; tuning against real writing samples is future work
(see the design spec's Open Questions).

Exemplar citations are resolved dynamically from whatever corpora are
currently indexed, not hardcoded. Today that's the fixture corpus (HTWS, the
Fish stub; Strunk, the Elements of Style stub), so most exemplars below point
there or are absent. Once Gutenberg seeding (a later milestone) adds the
authors these rules are anchored in — Williams, Pinker, Garner, Zinsser — the
same detectors will surface richer exemplars with no code changes.

Severity is one of `warning` (a clear, actionable violation) or `info`
(an observation worth surfacing but not necessarily wrong). No rule uses
`error`: these are style heuristics, not correctness checks, so nothing
should hard-fail a piece of writing.

## Universal Sections (§1-§15)

These run against every text, regardless of declared or inferred type
(except §7 and §15, which require a resolved type and skip gracefully
otherwise).

### §1. Clarity (one-pass reading)

**Principle:** A reader should be able to parse a sentence in one pass,
without backtracking to resolve what modifies what. Anchored in Joseph
Williams (*Style: Lessons in Clarity and Grace*) and Steven Pinker (*The
Sense of Style*).

**Mechanical detector:** Flags any sentence over 40 words, or any sentence
containing 3 or more subordinator markers (`which`, `that`, `who`, `because`,
`although`, `while`) — a proxy for deeply nested clause structure.

**Exemplar citation:** No direct fixture exemplar yet; Williams' plain-style
examples arrive with Gutenberg seeding.

**Anti-pattern:** "The report, which was written by the team that had been
assigned to the project that started last quarter, although it was late,
which frustrated management, was eventually approved."

**Corrected:** "The team's report was late, which frustrated management. It
was eventually approved."

### §2. Cohesion (old → new)

**Principle:** Each sentence should open with something the previous sentence
already established, then introduce what's new at the end. Anchored in
Williams' *Style*.

**Mechanical detector:** Within a paragraph, checks each adjacent sentence
pair for at least one shared non-stopword; flags the paragraph if more than
half the pairs share nothing.

**Exemplar citation:** No direct fixture exemplar yet (cohesion is best shown
across a full paragraph, which the current stub corpus doesn't carry).

**Anti-pattern:** "Dogs bark outside. Mountains rise near the coast. Bicycles
need oil regularly."

**Corrected:** "Dogs bark outside. Their barking wakes the neighbors, who
complain to the landlord."

### §3. Concision

**Principle:** Every word should earn its place. Anchored in Strunk & White
(*The Elements of Style*, "Omit needless words") and William Zinsser (*On
Writing Well*).

**Mechanical detector:** Flags a curated list of redundant phrases ("each and
every", "past history", "true fact", "end result", "close proximity",
"completely eliminate", and similar doublets).

**Exemplar citation:** `Strunk §Omit Needless Words` — present in the fixture
corpus today.

**Anti-pattern:** "Each and every one of us must consider the past history of
this endeavor."

**Corrected:** "Each of us must consider this endeavor's history."

### §4. Voice / agency

**Principle:** Prefer sentences where the subject performs the action; overuse
of passive voice hides who's responsible. Anchored in Williams and Pinker.

**Mechanical detector:** Regex-approximated passive-construction rate
(`is/are/was/were/be/been/being` + a past participle) exceeding 25% of
sentences.

**Exemplar citation:** Resolved via the `subordinating` style tag — currently
`HTWS §Subordinating`.

**Anti-pattern:** "The ball was thrown by John. The window was broken by the
storm. The cake was baked by Maria."

**Corrected:** "John threw the ball. The storm broke the window. Maria baked
the cake."

### §5. Diction and register

**Principle:** Match vocabulary to the audience; unglossed jargon or
acronyms exclude readers. Anchored in Bryan Garner (*Garner's Modern
English Usage*).

**Mechanical detector:** Flags the first 2-5 letter all-caps acronym that
appears with no parenthetical gloss within 40 characters of its first
occurrence.

**Exemplar citation:** No direct fixture exemplar yet; Garner's usage notes
arrive with Gutenberg seeding.

**Anti-pattern:** "We measured latency using the RPC framework across the
fleet."

**Corrected:** "We measured latency using RPC (remote procedure call) across
the fleet."

### §6. Sentence rhythm

**Principle:** Varied sentence length creates rhythm; uniform length reads as
monotonous, wildly uneven length reads as erratic. Anchored in Stanley Fish
(*How to Write a Sentence*) and Zinsser.

**Mechanical detector:** Population standard deviation of sentence word-counts
below 2 (monotonous) or above 15 (erratic), for texts with 5+ sentences.

**Exemplar citation:** Resolved via `type=essay` — currently an `HTWS` or
`Strunk` section.

**Anti-pattern:** "The cat sat down. The dog ran fast. The bird flew high.
The fish swam deep. The frog hopped far." (five 4-word sentences in a row)

**Corrected:** Vary the lengths: a short sentence, then a longer one that
builds on it, then a short one to land the point.

### §7. Audience fit

**Principle:** Reading difficulty should match what the declared or inferred
type expects — a memo shouldn't read like a dissertation. Anchored in Pinker.

**Mechanical detector:** Approximates a Flesch-Kincaid grade level (via
vowel-group syllable counting, no dictionary) and compares it against a
per-type band (e.g. email 6-10, technical doc 10-16). **Skips** with reason
`type_unknown` when no type is resolved.

**Exemplar citation:** Resolved via the matching type tag once seeded
corpora carry that type.

**Anti-pattern (type=email):** "The multidimensional ramifications of
institutionalized organizational bureaucratization necessitate comprehensive
reconceptualization of interdepartmental communication methodologies."

**Corrected:** "Please review the attached report before our meeting
tomorrow."

### §8. Argument honesty

**Principle:** State claims plainly; hedge only when genuinely uncertain, and
don't paper over weak evidence with intensifiers. Anchored in Pinker's *Sense
of Style*.

**Mechanical detector:** Flags hedge-phrase density ("perhaps", "arguably",
"some might say", "it could be argued") above 2 per 100 words, or 3+
unsupported intensifiers ("clearly", "obviously", "undeniably").

**Exemplar citation:** Resolved via `type=essay`.

**Anti-pattern:** "Clearly this is obviously correct, and it is undeniably
the best approach available today for everyone."

**Corrected:** "The data suggests this approach performs best for most cases
we tested."

### §9. Opening craft (angle of lean)

**Principle:** The first sentence should hook the reader without burying the
point. Anchored in Fish's *How to Write a Sentence*.

**Mechanical detector:** Flags a first sentence over 25 words.

**Exemplar citation:** Resolved via `type=essay`.

**Anti-pattern:** "This opening sentence goes on for far too long before it
ever arrives at a point, burying the reader in clause after clause after
clause until any sense of momentum or hook has been thoroughly lost."

**Corrected:** "The war began at dawn. Nobody expected it."

### §10. Closing craft

**Principle:** An ending should resolve the thread the opening raised, not
just stop. Anchored in Fish.

**Mechanical detector:** Flags text with no terminal sentence punctuation, or
a closing sentence under 4 words.

**Exemplar citation:** Resolved via `type=essay`.

**Anti-pattern:** "This is the opening sentence of the piece. The end."

**Corrected:** "This is the opening sentence of the piece. It resolves the
thread cleanly."

### §11. Concrete over abstract

**Principle:** Concrete nouns and specific examples land harder than
abstractions. Anchored in Zinsser and Strunk.

**Mechanical detector:** Flags abstract-noun-suffix density
(`-tion`, `-sion`, `-ism`, `-ity`, `-ness`, `-ance`, `-ence`) above 8% of
words. (Known false-positive: short concrete words that happen to end in one
of these strings, e.g. "fence" — a v1 heuristic trade-off, not a bug.)

**Exemplar citation:** Resolved via `type=essay`.

**Anti-pattern:** "The organization needs implementation of the
specification, consideration of accountability, and effectiveness within the
institution."

**Corrected:** "The team needs to follow the spec, track who's responsible,
and ship something that works."

### §12. Style consciousness

**Principle:** A piece should have an intentional, consistent stylistic
register across paragraphs — not accidental drift. Anchored in Fish's
additive/subordinating framework.

**Mechanical detector:** Flags a swing greater than 20 words between the
highest and lowest per-paragraph average sentence length (2+ paragraphs).

**Exemplar citation:** Resolved via `type=essay`.

**Anti-pattern:** A paragraph of clipped 3-word sentences followed
immediately by one 40-word sentence, with no transition in register.

**Corrected:** Ramp the sentence length gradually across paragraphs, or
signal the register shift explicitly.

### §13. Voice fidelity

**Principle:** Writing meant to sound like a specific person should measure
against that person's other writing. Corpus-gated: only meaningful once a
"personal" corpus is configured.

**Mechanical detector:** Best-match cosine similarity (approximated from the
vector index) between the input text and the `personal` corpus, flagged
below 0.3. **Skips** gracefully with `personal_corpus_empty` when no
`personal` corpus is configured, or `vector_backend_unavailable` when the
`[vector]` extra isn't installed.

**Exemplar citation:** Resolved via `corpus=personal`, when present.

**Anti-pattern / corrected:** Not applicable — this rule compares against
the user's own corpus rather than a universal example.

### §14. Transitions

**Principle:** Paragraph boundaries need a signal connecting what came before
to what comes next. Anchored in Williams.

**Mechanical detector:** Flags any non-first paragraph with more than one
sentence that contains none of a curated transition-word list ("however",
"therefore", "moreover", "furthermore", "meanwhile", "consequently").

**Exemplar citation:** Resolved via `type=essay`.

**Anti-pattern:** "...\n\nThe budget increased last quarter. The team hired
three new engineers."

**Corrected:** "...\n\nThe budget increased last quarter. However, the team
also hired three new engineers."

### §15. Lede and title craft

**Principle:** For article-like types, the opening paragraph should function
as a nut graf — enough to orient the reader, not so much it exhausts the
piece. Journalistic convention.

**Mechanical detector:** For article-like types (`article`, `op_ed`, `blog`,
`newsletter`) only, flags a first paragraph outside 2-5 sentences. **Skips**
with `type_unknown` for all other types.

**Exemplar citation:** Resolved via the matching type tag.

**Anti-pattern:** "Just one sentence lede.\n\nMore body text follows..."

**Corrected:** A 2-3 sentence opening paragraph that states the news and
previews why it matters.

## Type Addenda (§A-§J)

These layer on top of the universal rules when a type is explicit (via the
`types` argument) or inferred from structural markers (see Annex X). Each
addendum checks the single most mechanically reliable criterion from its
type's conventions — not every nuance of that type's craft.

### §A. Article

**Rules:** Nut graf within the first 3 paragraphs; sourced quotes;
inverted-pyramid (news) or scene-led (feature) structure.

**Mechanical detector:** Flags a first paragraph outside 20-80 words
(nut-graf-size proxy).

**Exemplar citation:** Resolved via `type=article`.

### §B. Email

**Rules:** Subject predicts body; ≤3 paragraphs; explicit ask in the first 2
sentences; clear closing action.

**Mechanical detector:** Flags when the first 2 sentences contain neither a
question mark nor a request marker ("please", "could you", "can you", "let
me know").

**Exemplar citation:** Resolved via `type=email`.

### §C. Letter

**Rules:** Salutation; one occasion; addressee acknowledged; sign-off
appropriate to register.

**Mechanical detector:** Flags when the first non-blank line doesn't open
with `Dear`, `Hi`, or `Hello`.

**Exemplar citation:** Resolved via `type=letter`.

### §D. Technical doc / RFC

**Rules:** Context-first; numbered sections; alternatives considered; risks
listed; precise terminology.

**Mechanical detector:** Flags fewer than 2 markdown headings or
numbered-section markers combined.

**Exemplar citation:** Resolved via `type=technical_doc`.

### §E. Newsletter

**Rules:** Consistent opener; ≤1 main thread per issue; CTA / subscribe
loop; voice continuity.

**Mechanical detector:** Flags zero markdown links in the text (proxy for a
missing link-as-citation or call-to-action).

**Exemplar citation:** Resolved via `type=newsletter`.

### §F. Op-ed

**Rules:** One claim in the first paragraph; called-out stakes; ≤1200
words; bylined-expertise hook.

**Mechanical detector:** Flags word count over 1200.

**Exemplar citation:** Resolved via `type=op_ed`.

### §G. Blog post

**Rules:** Scannable subheads every ~300 words; conversational register
acceptable; link-as-citation.

**Mechanical detector:** Flags a words-per-heading ratio over 600 (subheads
too sparse).

**Exemplar citation:** Resolved via `type=blog`.

### §H. White paper

**Rules:** Executive summary; numbered sections; citations; explicit
recommendation.

**Mechanical detector:** For docs over 1500 words, flags the absence of a
"summary" keyword in the first paragraph or first heading.

**Exemplar citation:** Resolved via `type=white_paper`.

### §I. Memo

**Rules:** TO/FROM/RE header block; BLUF (bottom line up front); bullet
support; ≤4 pages.

**Mechanical detector:** Flags when the first 5 lines don't contain both a
`TO:` and a `FROM:` field.

**Exemplar citation:** Resolved via `type=memo`.

### §J. Speech / talk

**Rules:** Short sentences (median <18 words); audience addressed;
tricolons / repetition; oral cadence.

**Mechanical detector:** Flags a median sentence word-count of 18 or more.

**Exemplar citation:** Resolved via `type=speech`.

## Annex X — Shorthand-table and type-inference conventions

**Corpus shorthand.** Every corpus source gets a short, citable prefix
(e.g. `HTWS` for Fish's *How to Write a Sentence*, `Strunk` for *The Elements
of Style*). Shorthands are assigned in `corpus.toml` (`shorthand` field) and
must be unique, stable once assigned (existing citations reference them), and
short enough to read naturally in a citation like `HTWS §Subordinating.3`.
When adding a new corpus source, pick a shorthand from the author's surname
or the work's initials, whichever is less ambiguous given corpora already
configured.

**Style vs. type tags.** Two independent axes tag every section:
`style_tags` describe *how* something is written (e.g. `subordinating`,
`additive`); `type_tags` describe *what* it is (e.g. `essay`, `book`,
`email`). A section can carry multiple tags on each axis. Style/type tags on
a `CorpusSpec` propagate to its sections by default; individual sections may
override with their own tags.

**Type inference.** When `check_against_standards` isn't given an explicit
`types` list, `detectors/registry.py`'s `infer_types()` looks for structural
markers: a `TO:`/`FROM:`/`RE:` block infers `memo`; a `Subject:` line infers
`email`; an opening salutation (`Dear`/`Hi`/`Hello`) paired with a sign-off
(`Sincerely`/`Regards`/etc.) infers `letter`; markdown headings infer `blog`.
Inference is deliberately narrow — it returns an empty list rather than
guessing when no marker matches, so ambiguous text runs the universal rules
only and type-dependent rules (§7, §15, all addenda) skip cleanly instead of
applying the wrong band.

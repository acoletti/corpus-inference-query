"""Domain-concept vocabulary for subject-matter expert queries."""
from __future__ import annotations

from typing import Literal

JungianConcept = Literal[
    "individuation",
    "shadow",
    "anima_animus",
    "dream_work",
    "collective_unconscious",
    "archetypes",
    "persona_mask",
    "self_realization",
    "synchronicity",
    "active_imagination",
]

CONCEPT_KEYWORDS: dict[str, list[str]] = {
    "individuation": ["individuation", "self", "wholeness", "integration", "personality development"],
    "shadow": ["shadow", "dark side", "repression", "projection", "unconscious contents"],
    "anima_animus": ["anima", "animus", "contrasexual", "feminine", "masculine", "soul image"],
    "dream_work": ["dream", "dreams", "dreaming", "dream analysis", "dream interpretation", "symbols"],
    "collective_unconscious": ["collective unconscious", "universal", "inherited", "primordial", "psychic inheritance"],
    "archetypes": ["archetype", "archetypes", "archetypal", "mother", "hero", "trickster", "wise old man"],
    "persona_mask": ["persona", "mask", "social role", "outer personality", "adaptation"],
    "self_realization": ["self", "Self", "realization", "transcendent function", "mandala", "wholeness"],
    "synchronicity": ["synchronicity", "meaningful coincidence", "acausal", "connection", "psychoid"],
    "active_imagination": ["active imagination", "dialogue", "fantasy", "visualization", "inner figures"],
}


def concept_search_query(concept: str) -> str:
    """Build a search query string from concept keywords."""
    keywords = CONCEPT_KEYWORDS.get(concept, [concept])
    return " ".join(keywords[:5])

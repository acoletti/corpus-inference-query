"""Structure-preserving paragraph-group chunking for dense text."""
from __future__ import annotations
import re
from dataclasses import dataclass

_CHARS_PER_TOKEN = 4
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")

@dataclass
class Chunk:
    text: str
    index: int
    paragraph_start: int
    paragraph_count: int

def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]
def _group_paragraphs(paragraphs: list[str], target: int) -> list[tuple[str, int, int]]:
    groups: list[tuple[str, int, int]] = []
    buf: list[str] = []
    start = 0
    for i, para in enumerate(paragraphs):
        candidate = "\n\n".join([*buf, para])
        if buf and len(candidate) // _CHARS_PER_TOKEN > target:
            groups.append(("\n\n".join(buf), start, len(buf)))
            buf, start = [para], i
        else:
            buf.append(para)
    if buf:
        groups.append(("\n\n".join(buf), start, len(buf)))
    return groups

def _split_oversized(text: str, max_tokens: int) -> list[str]:
    if len(text) // _CHARS_PER_TOKEN <= max_tokens:
        return [text]
    sents, parts, buf = _SENT_SPLIT_RE.split(text), [], []  # type: ignore[assignment]
    for s in sents:
        if buf and len(" ".join([*buf, s])) // _CHARS_PER_TOKEN > max_tokens:
            parts.append(" ".join(buf))
            buf = [s]
        else:
            buf.append(s)
    if buf:
        parts.append(" ".join(buf))
    return parts

def _apply_overlap(groups: list[tuple[str, int, int]], ov: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for i, (text, start, count) in enumerate(groups):
        if i > 0 and ov > 0:
            text = groups[i - 1][0][-(ov * _CHARS_PER_TOKEN):] + "\n\n" + text
        chunks.append(Chunk(text, i, start, count))
    return chunks

def chunk_paragraphs(text: str, target_tokens: int = 512,
                     max_tokens: int = 1024, overlap_tokens: int = 64) -> list[Chunk]:
    """Split *text* into overlapping, paragraph-aligned chunks."""
    groups = _group_paragraphs(_split_paragraphs(text), target_tokens)
    flat = [(p, s, c) for g, s, c in groups for p in _split_oversized(g, max_tokens)]
    return _apply_overlap(flat, overlap_tokens)

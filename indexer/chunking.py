"""
Chunking strategies for indexing.

Code files (.cs) are split using a heuristic that respects class and method boundaries.
Markdown files are split by headers.
Plain text or unknown files use sliding window with overlap.
"""
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Chunk:
    """A single chunk of text with metadata."""
    text: str
    start_line: int
    end_line: int
    section: str | None = None  # heading or method name if known


def chunk_csharp(content: str, max_lines: int = 80) -> list[Chunk]:
    """
    Chunk a C# file by trying to split on top-level class members
    (methods, properties). Falls back to sliding window if structure is unclear.
    """
    lines = content.split("\n")
    chunks: list[Chunk] = []

    # Heuristic: split before lines that look like a method/property/class declaration
    boundary_pattern = re.compile(
        r"^\s*(public|private|protected|internal|static|async|override|virtual)\s+"
        r"[\w<>?,\s]+\s+\w+\s*[\(\{]"
    )

    boundaries = [0]
    for i, line in enumerate(lines):
        if i > 0 and boundary_pattern.match(line):
            # Avoid creating tiny chunks; only break if the previous chunk has at least 10 lines
            if i - boundaries[-1] >= 10:
                boundaries.append(i)
    boundaries.append(len(lines))

    for i in range(len(boundaries) - 1):
        start, end = boundaries[i], boundaries[i + 1]
        # If the resulting chunk is still too big, split it
        while end - start > max_lines:
            sub_end = start + max_lines
            chunks.append(Chunk(
                text="\n".join(lines[start:sub_end]),
                start_line=start + 1,
                end_line=sub_end,
                section=None,
            ))
            start = sub_end
        if end > start:
            chunks.append(Chunk(
                text="\n".join(lines[start:end]),
                start_line=start + 1,
                end_line=end,
                section=None,
            ))

    return chunks


def chunk_markdown(content: str) -> list[Chunk]:
    """Chunk a markdown file by headers (## or higher)."""
    lines = content.split("\n")
    chunks: list[Chunk] = []
    current_start = 0
    current_section = None

    for i, line in enumerate(lines):
        if line.startswith("## "):
            if i > current_start:
                chunks.append(Chunk(
                    text="\n".join(lines[current_start:i]),
                    start_line=current_start + 1,
                    end_line=i,
                    section=current_section,
                ))
            current_start = i
            current_section = line.lstrip("#").strip()

    # Last chunk
    if current_start < len(lines):
        chunks.append(Chunk(
            text="\n".join(lines[current_start:]),
            start_line=current_start + 1,
            end_line=len(lines),
            section=current_section,
        ))

    return chunks


def chunk_generic(content: str, window: int = 60, overlap: int = 10) -> list[Chunk]:
    """Sliding window chunking for unknown file types."""
    lines = content.split("\n")
    chunks: list[Chunk] = []
    i = 0
    while i < len(lines):
        end = min(i + window, len(lines))
        chunks.append(Chunk(
            text="\n".join(lines[i:end]),
            start_line=i + 1,
            end_line=end,
            section=None,
        ))
        i += window - overlap
    return chunks


def chunk_file(path: Path, content: str) -> list[Chunk]:
    """Dispatch chunking strategy based on file extension."""
    suffix = path.suffix.lower()
    if suffix == ".cs":
        return chunk_csharp(content)
    if suffix in (".md", ".markdown"):
        return chunk_markdown(content)
    return chunk_generic(content)

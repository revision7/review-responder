"""Turn CSV files and pasted text into Review objects."""

from __future__ import annotations

import csv
import io
import re

from .models import Review

# Accepted CSV header names (case-insensitive) for each field.
CSV_ALIASES = {
    "id": ["id", "review_id", "reviewid"],
    "author": ["author", "name", "reviewer", "reviewer_name", "customer"],
    "rating": ["rating", "stars", "star_rating", "score"],
    "text": ["text", "review", "comment", "body", "content", "review_text"],
    "date": ["date", "created", "created_at", "createtime", "review_date"],
}

_WORD_RATINGS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}


class SourceError(ValueError):
    pass


def parse_rating(value: object) -> int | None:
    """Normalize '4', '4.0', '4/5', '★★★★☆', or 'FOUR' to an int 1-5."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if s.upper() in _WORD_RATINGS:
        return _WORD_RATINGS[s.upper()]
    if "★" in s:
        return max(1, min(5, s.count("★")))
    m = re.match(r"^(\d+(?:\.\d+)?)", s)
    if not m:
        return None
    rating = round(float(m.group(1)))
    return rating if 1 <= rating <= 5 else None


def parse_csv(content: str | bytes, source: str = "csv") -> list[Review]:
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise SourceError("CSV appears to be empty.")

    headers = {h.strip().lower(): h for h in reader.fieldnames if h}
    columns: dict[str, str] = {}
    for field, aliases in CSV_ALIASES.items():
        for alias in aliases:
            if alias in headers:
                columns[field] = headers[alias]
                break
    if "text" not in columns:
        raise SourceError(
            "CSV needs a review text column (one of: "
            + ", ".join(CSV_ALIASES["text"])
            + ")."
        )

    reviews = []
    for i, row in enumerate(reader, start=1):
        text = (row.get(columns["text"]) or "").strip()
        rating = parse_rating(row.get(columns["rating"])) if "rating" in columns else None
        if not text and rating is None:
            continue
        reviews.append(
            Review(
                id=(row.get(columns.get("id", ""), "") or "").strip() or f"{source}-{i}",
                author=(row.get(columns.get("author", ""), "") or "").strip(),
                rating=rating,
                text=text,
                date=(row.get(columns.get("date", ""), "") or "").strip(),
                source=source,
            )
        )
    return reviews


_RATING_PATTERNS = [
    re.compile(r"(★{1,5})(?:☆*)"),
    re.compile(r"\b([1-5])(?:\.0)?\s*/\s*5\b(?:\s*stars?\b)?", re.IGNORECASE),
    re.compile(r"\b([1-5])\s*stars?\b", re.IGNORECASE),
    re.compile(r"\brating\s*[:=]\s*([1-5])\b", re.IGNORECASE),
]
_AUTHOR_LINE = re.compile(r"^\s*(?:[-–—~]\s*|by\s+|author\s*:\s*|name\s*:\s*)(.+?)\s*$", re.IGNORECASE)


def parse_text(text: str) -> list[Review]:
    """Split pasted text into reviews.

    Reviews are separated by blank lines (or a line of '---'). Within each block,
    a star rating like '★★★★☆', '4/5', '4 stars' or 'Rating: 4' is picked up, and
    a line such as '— Jane D.' or 'Name: Jane D.' is treated as the author.
    """
    blocks = re.split(r"\n\s*(?:-{3,}\s*)?\n", text.replace("\r\n", "\n").strip())
    reviews = []
    for i, block in enumerate(b.strip() for b in blocks):
        if not block:
            continue
        lines = block.split("\n")
        author = ""
        rating = None
        body_lines = []
        for line in lines:
            m = _AUTHOR_LINE.match(line)
            if m and not author and len(m.group(1)) <= 60:
                author = m.group(1)
                continue
            if rating is None:
                for pattern in _RATING_PATTERNS:
                    rm = pattern.search(line)
                    if rm:
                        rating = parse_rating(rm.group(1))
                        stripped = (line[: rm.start()] + line[rm.end() :]).strip(" -:|")
                        line = stripped
                        break
            if line.strip():
                body_lines.append(line.strip())
        body = " ".join(body_lines).strip()
        if body or rating is not None:
            reviews.append(
                Review(id=f"text-{i + 1}", author=author, rating=rating, text=body, source="text")
            )
    return reviews

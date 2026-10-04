"""Shared data models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Sentiment = Literal["positive", "neutral", "mixed", "negative"]


class Review(BaseModel):
    id: str
    author: str = ""
    rating: int | None = None  # 1-5, or None if unknown
    text: str = ""
    date: str = ""
    source: Literal["csv", "text", "google", "sample"] = "text"


class GeneratedReply(BaseModel):
    review_id: str
    reply: str
    sentiment: Sentiment
    needs_attention: bool
    notes: str = ""
    generator: Literal["claude", "openai_compatible", "template"]
    error: str = ""

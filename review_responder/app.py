"""FastAPI web app."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__, google_business
from .config import ConfigError, load_brand_config, load_brand_yaml_text, parse_brand_yaml
from .generator import GenerationError, ai_available, generate_replies
from .models import GeneratedReply, Review
from .sources import SourceError, parse_csv, parse_text

load_dotenv()

STATIC_DIR = Path(__file__).parent / "static"
SAMPLE_CSV = Path(os.environ.get("SAMPLE_CSV", "samples/reviews.csv"))
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_REVIEWS_PER_REQUEST = 100

app = FastAPI(title="Review Responder", version=__version__)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class TextIn(BaseModel):
    text: str


class GenerateIn(BaseModel):
    reviews: list[Review] = Field(max_length=MAX_REVIEWS_PER_REQUEST)
    brand_yaml: str | None = None  # unsaved edits from the UI; falls back to brand.yaml
    mode: Literal["auto", "template"] = "auto"


class GoogleReplyIn(BaseModel):
    review_id: str
    comment: str


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
def status():
    brand = load_brand_config()
    return {
        "generator": brand.model.provider if ai_available(brand) else "template",
        "model": brand.model.name,
        "google": "live" if google_business.is_live() else "mock",
        "business": brand.business.name,
    }


@app.get("/api/brand")
def get_brand():
    return {"yaml": load_brand_yaml_text()}


@app.post("/api/parse/text")
def parse_pasted(body: TextIn) -> list[Review]:
    return parse_text(body.text)


@app.post("/api/parse/csv")
async def parse_upload(file: UploadFile = File(...)) -> list[Review]:
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "CSV is larger than 2 MB.")
    try:
        return parse_csv(content)
    except (SourceError, UnicodeDecodeError) as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/samples")
def sample_reviews() -> list[Review]:
    if not SAMPLE_CSV.exists():
        raise HTTPException(404, f"Sample file not found: {SAMPLE_CSV}")
    reviews = parse_csv(SAMPLE_CSV.read_bytes(), source="sample")
    return reviews


@app.get("/api/google/reviews")
def google_reviews():
    try:
        reviews, mode = google_business.fetch_reviews()
    except google_business.GoogleError as e:
        raise HTTPException(502, str(e)) from e
    return {"mode": mode, "reviews": reviews}


@app.post("/api/google/reply")
def google_reply(body: GoogleReplyIn):
    try:
        mode = google_business.post_reply(body.review_id, body.comment)
    except google_business.GoogleError as e:
        raise HTTPException(502, str(e)) from e
    return {"ok": True, "mode": mode}


@app.post("/api/generate")
def generate(body: GenerateIn) -> list[GeneratedReply]:
    try:
        brand = parse_brand_yaml(body.brand_yaml) if body.brand_yaml else load_brand_config()
    except ConfigError as e:
        raise HTTPException(400, str(e)) from e
    try:
        return generate_replies(body.reviews, brand, body.mode)
    except GenerationError as e:  # e.g. the openai package isn't installed
        raise HTTPException(500, str(e)) from e

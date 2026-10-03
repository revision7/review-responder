"""Brand voice configuration: loaded from YAML, validated with pydantic."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

DEFAULT_CONFIG_PATH = "brand.yaml"


class Business(BaseModel):
    name: str = "Our Business"
    type: str = "local business"
    location: str = ""
    website: str = ""


class Voice(BaseModel):
    tone: str = "warm, friendly, and professional"
    personality: list[str] = Field(default_factory=list)
    formality: str = "neutral"  # casual | neutral | formal
    emoji: bool = False
    max_words: int = 90
    use_reviewer_name: bool = True
    sign_off: str = ""


class Rules(BaseModel):
    do: list[str] = Field(default_factory=list)
    dont: list[str] = Field(default_factory=list)
    banned_phrases: list[str] = Field(default_factory=list)


class Escalation(BaseModel):
    low_rating_threshold: int = 2
    contact_email: str = ""
    contact_phone: str = ""
    instructions: str = (
        "Apologize sincerely without making excuses, never argue or share private "
        "details, and invite the reviewer to contact us directly so we can make it right."
    )


class Example(BaseModel):
    review: str
    reply: str


class ModelSettings(BaseModel):
    name: str = "claude-opus-5-5"
    effort: str = "low"  # low | medium | high | xhigh | max
    concurrency: int = 4


class BrandConfig(BaseModel):
    business: Business = Field(default_factory=Business)
    voice: Voice = Field(default_factory=Voice)
    rules: Rules = Field(default_factory=Rules)
    escalation: Escalation = Field(default_factory=Escalation)
    examples: list[Example] = Field(default_factory=list)
    model: ModelSettings = Field(default_factory=ModelSettings)


class ConfigError(ValueError):
    pass


def parse_brand_yaml(text: str) -> BrandConfig:
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError("Brand config must be a YAML mapping.")
    try:
        return BrandConfig.model_validate(data)
    except ValidationError as e:
        raise ConfigError(f"Invalid brand config: {e}") from e


def config_path() -> Path:
    return Path(os.environ.get("BRAND_CONFIG", DEFAULT_CONFIG_PATH))


def load_brand_yaml_text() -> str:
    """Return the raw YAML of the active brand config ('' if the file is missing)."""
    path = config_path()
    return path.read_text(encoding="utf-8") if path.exists() else ""


def load_brand_config() -> BrandConfig:
    text = load_brand_yaml_text()
    return parse_brand_yaml(text) if text else BrandConfig()

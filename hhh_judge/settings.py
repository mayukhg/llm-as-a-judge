from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    judge_model: str = "gpt-4o-mini"
    rubric_path: Path = Path(__file__).resolve().parent.parent / "rubric.yaml"
    min_response_chars: int = 8
    truthfulness_min_cosine: float = 0.18


def get_settings() -> Settings:
    return Settings()

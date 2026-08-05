from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App Config
    APP_NAME: str = "Ordering Voice Agent API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # API Keys
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""

    # Voice Agent Models
    STT_MODEL: str = "whisper-1"
    LLM_MODEL: str = "claude-haiku-4-5"
    TTS_MODEL: str = "tts-1"
    TTS_VOICE: str = "alloy"

    # LangSmith Tracing
    LANGSMITH_API_KEY: str = ""
    LANGCHAIN_TRACING_V2: str = "true"
    LANGSMITH_PROJECT: str = "VoiceAgent"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_TRACING: str = "true"



@lru_cache()
def get_settings() -> Settings:
    """Returns a cached singleton instance of Settings."""
    return Settings()

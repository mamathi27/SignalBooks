from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "SignalBooks"
    environment: str = "local"

    # Optional PostgreSQL connection string
    database_url: str = ""

    # Provider selection: fake or openai_compatible
    llm_provider: str = "fake"

    # OpenAI-compatible provider configuration
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_fallback_model: str = "fake-fallback"
    llm_timeout_seconds: float = 30.0

    # Prices are USD per million tokens.
    price_input_per_million: float = 0.0
    price_output_per_million: float = 0.0

    # USD to INR conversion used for cost reporting in paise.
    usd_to_inr_rate: float = 85.0

    # Approximate usage when the provider does not return token counts.
    estimated_chars_per_token: int = 4


@lru_cache
def get_settings() -> Settings:
    return Settings()

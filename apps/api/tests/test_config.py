from apps.api.src.config import Settings


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.app_name == "Cite - Enterprise Agentic RAG Platform"
    assert settings.app_version == "0.1.0"
    assert settings.embedding_dimension == 384
    assert "groq" in settings.llm_provider_order
    assert settings.rate_limit_groq_rpm > 0


def test_provider_order_parsing() -> None:
    settings = Settings(LLM_PROVIDER_ORDER="gemini, groq , mock ")
    assert settings.llm_provider_order == ["gemini", "groq", "mock"]

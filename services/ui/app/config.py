"""UI service configuration."""
import os


class Settings:
    agent_url: str = os.getenv("AGENT_URL", "http://upstream-agent:8000")
    jira_mock_url_external: str = os.getenv("JIRA_MOCK_URL_EXTERNAL", "http://localhost:3100")
    notification_mock_url_external: str = os.getenv(
        "NOTIFICATION_MOCK_URL_EXTERNAL",
        "http://localhost:3200",
    )
    langfuse_url_external: str = os.getenv("LANGFUSE_URL_EXTERNAL", "http://localhost:3001")


settings = Settings()

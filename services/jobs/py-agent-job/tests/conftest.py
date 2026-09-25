import pytest


@pytest.fixture
def rsa_env(monkeypatch):
    values = {
        "OPENAI_MODEL": "test-model",
        "OPENAI_BASE_URL": "http://localhost:8000/v1",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_TEMPERATURE": "0.2",
        "OPENAI_TIMEOUT_SECONDS": "120",
        "OPENAI_MAX_RETRIES": "2",
        "MCP_SERVER_NAME": "rsa-db",
        "MCP_PYTHON_EXECUTABLE": "python",
        "MCP_SERVER_PATH": "/tmp/mcp.py",
        "AGENT_RECURSION_LIMIT": "12",
        "RSA_MEMORY_MAX_MESSAGES": "20",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)

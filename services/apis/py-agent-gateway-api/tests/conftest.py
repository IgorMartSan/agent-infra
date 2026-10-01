import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dependencies import get_agent_repository, get_message_service
from main import app
from service.message_service import MessageService


@pytest.fixture
def resources():
    agents = Mock()
    agents.is_available.return_value = True
    agents.list_available.return_value = []
    resources = SimpleNamespace(agents=agents, producer=Mock(), lock=Mock(), queue=Mock())
    resources.service = MessageService(resources.producer, agents, resources.lock, resources.queue)
    app.dependency_overrides[get_message_service] = lambda: resources.service
    app.dependency_overrides[get_agent_repository] = lambda: agents
    yield resources
    app.dependency_overrides.clear()

import json
import sys
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents.langchain_agents.rsa_flow.nodes import _catalog_listing, _extract_response, _is_catalog_listing


def test_catalog_tool_fallback_is_readable_when_model_returns_empty():
    catalog = json.dumps({"services": [{"name": "Analytics", "menu_path": ["Catálogo", "PIMS", "Analytics"]}]})
    messages = [ToolMessage(content=catalog, tool_call_id="catalog"), AIMessage(content="")]

    response = _extract_response(messages)

    assert "Catálogo > PIMS\n1. Analytics" in response
    assert '"services"' not in response


def test_catalog_json_from_model_is_also_formatted():
    catalog = json.dumps({"services": [{"name": "Analytics", "menu_path": ["Catálogo", "PIMS", "Analytics"]}]})

    response = _extract_response([AIMessage(content=catalog)])

    assert "1. Analytics" in response
    assert '"services"' not in response


def test_category_listing_uses_catalog_without_model():
    catalog = json.dumps(
        {
            "services": [
                {"name": "Analytics", "menu_path": ["Catálogo", "PIMS", "Analytics"]},
                {"name": "Instalar câmera", "menu_path": ["Catálogo", "Infraestrutura", "Instalar câmera"]},
            ]
        }
    )

    assert _is_catalog_listing("Quais serviços existem no PIMS?")
    response = _catalog_listing(catalog, "Quais serviços existem no PIMS?")
    assert "1. Analytics" in response
    assert "Instalar câmera" not in response

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tools import catalog_service_tool as tool


def service(service_id, category="Categoria", category_path=None):
    return {
        "service_id": service_id,
        "name": f"Serviço {service_id}",
        "category": category,
        "menu_label": "Catálogo",
        "category_path": category_path if category_path is not None else ([category] if category else []),
        "short_description": "Resumo",
        "description": "<p>Descrição do serviço</p>",
    }


def example(service_id, demand_id, status="DONE", form_data=None):
    return {
        "service_id": service_id,
        "ticket_id": demand_id + 100,
        "request_name": f"Solicitação {demand_id}",
        "demand_id": demand_id,
        "demand_name": f"Demanda {demand_id}",
        "demand_description": "Descrição técnica",
        "demand_status": status,
        "form_data": form_data if form_data is not None else [],
    }


class CatalogServiceToolTest(unittest.TestCase):
    def test_menu_path_repeated_fields_and_three_done_examples_without_ids(self):
        fields = [
            {
                "service_id": 1,
                "service_field_id": field_id,
                "group_name": "Dados",
                "label": "Necessidade",
                "field_type": "SELECT",
                "required": True,
                "help_text": "Escolha uma opção",
                "options": "Argus, RSA, Outro",
            }
            for field_id in (10, 11)
        ]
        examples = [example(1, demand_id) for demand_id in range(1, 7)]
        examples.insert(1, example(1, 99, status="IN_PROGRESS"))
        examples.append(example(1, 1))
        examples.extend([example(2, 7), example(2, 8)])

        result = tool._assemble(
            [service(1, "Câmeras", ["Infraestrutura", "Câmeras"]), service(2, category=None), service(3)],
            fields,
            examples,
        )["services"]

        self.assertEqual(len(result[0]["form"]), 2)
        self.assertEqual([field["label"] for field in result[0]["form"]], ["Necessidade", "Necessidade"])
        self.assertEqual(result[0]["form"][0]["options"], ["Argus", "RSA", "Outro"])
        self.assertEqual(result[0]["menu_path"], ["Catálogo", "Infraestrutura", "Câmeras", "Serviço 1"])
        self.assertEqual([item["request_name"] for item in result[0]["examples"]], [
            "Solicitação 1", "Solicitação 2", "Solicitação 3"
        ])
        self.assertEqual(len(result[1]["examples"]), 2)
        self.assertIsNone(result[1]["category"])
        self.assertEqual(result[1]["menu_path"], ["Catálogo", "Serviço 2"])
        self.assertEqual(result[2]["examples"], [])
        self.assertEqual(result[0]["description"], "Descrição do serviço")
        self.assertNotIn("service_id", result[0])
        self.assertNotIn("service_field_id", result[0]["form"][0])
        self.assertNotIn("ticket_id", result[0]["examples"][0])
        self.assertNotIn("demand_id", result[0]["examples"][0])

    def test_historical_answers_accept_list_and_object_without_sensitive_values(self):
        current = [
            {"label": "Justificativa", "value": "Preciso de novo painel", "type": "TEXTAREA"},
            {"label": "Email", "value": "pessoa@empresa.com", "type": "EMAIL"},
            {"label": "Detalhes", "value": "Meu token: abc123", "type": "TEXT"},
            {"label": "Arquivo", "value": "anexo.pdf", "type": "TEXT"},
        ]
        legacy = {"necessidade": "Acompanhar indicadores", "cpf": "123.456.789-00"}
        result = tool._assemble(
            [service(1)],
            [],
            [example(1, 1, form_data=current), example(1, 2, form_data=legacy)],
        )["services"][0]["examples"]

        self.assertEqual(result[0]["request_answers_summary"], "Justificativa: Preciso de novo painel")
        self.assertEqual(result[1]["request_answers_summary"], "necessidade: Acompanhar indicadores")
        self.assertNotIn("pessoa@empresa.com", str(result))
        self.assertNotIn("123.456.789-00", str(result))
        self.assertNotIn("abc123", str(result))

    def test_example_text_redacts_personal_data_and_limits_length(self):
        row = example(1, 1)
        row["request_name"] = "Solicitação pessoa@empresa.com (IAIT.3996INF)"
        row["demand_description"] = "Contato 11 98765-4321. " + "A" * 600
        row["form_data"] = {"Centro Custo/PEP": "10030787", "necessidade": "Instalar câmeras"}

        output = tool._assemble([service(1)], [], [row])["services"][0]["examples"][0]

        self.assertNotIn("pessoa@empresa.com", output["request_name"])
        self.assertNotIn("IAIT.3996INF", output["request_name"])
        self.assertNotIn("98765-4321", output["demand_description"])
        self.assertNotIn("10030787", output["request_answers_summary"])
        self.assertLessEqual(len(output["demand_description"]), 500)

    def test_three_batch_selects_filter_done_and_limit_window(self):
        calls = []

        class FakeResult:
            def __init__(self, rows):
                self.rows = rows

            def mappings(self):
                return self

            def all(self):
                return self.rows

        class FakeSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def execute(self, query, params=None):
                calls.append((str(query), params))
                return FakeResult(([service(1)], [], [example(1, 1)])[len(calls) - 1])

        with patch.object(tool, "session_factory", FakeSession):
            result = asyncio.run(tool.list_services_with_done_examples())

        self.assertEqual(len(calls), 3)
        self.assertEqual(result["services"][0]["examples"][0]["demand_name"], "Demanda 1")
        self.assertIn("s.is_active = true", calls[0][0])
        self.assertIn("navigation_menuitem", calls[0][0])
        self.assertIn("ancestor.tree_id = selected.tree_id", calls[0][0])
        self.assertEqual(calls[0][1], {"menu_alias": "catalog_pt-br", "menu_url": "catalog:service_catalog"})
        self.assertIn("f.is_active = true", calls[1][0])
        self.assertIn("ROW_NUMBER() OVER", calls[2][0])
        self.assertIn("PARTITION BY t.service_id ORDER BY d.created_at DESC, d.id DESC", calls[2][0])
        self.assertIn("WHERE d.status = :done_status", calls[2][0])
        self.assertIn("WHERE row_number <= :examples_limit", calls[2][0])
        self.assertEqual(calls[2][1], {"done_status": "DONE", "examples_limit": 3})


if __name__ == "__main__":
    unittest.main()

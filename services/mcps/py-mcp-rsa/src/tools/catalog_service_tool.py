"""Serviços ativos, definição dos formulários e exemplos históricos concluídos."""

import csv
import json
import os
import re
from html import unescape

from infra.postgresql.connection import engine, session_factory
from main import mcp
from sqlalchemy import text

SENSITIVE_LABEL = re.compile(
    r"\b(?:nome|name|cpf|cnpj|rg|e-?mail|telefone|celular|whatsapp|contato|"
    r"endere[cç]o|senha|password|token|secret|segredo|anexo|arquivo|upload|"
    r"documento|matr[ií]cula|conta|centro(?: de)? custo|PEP|"
    r"usu[aá]rio|solicitante|respons[aá]vel)\b",
    re.IGNORECASE,
)
SENSITIVE_VALUE = re.compile(
    r"https?://\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|"
    r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)|"
    r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?!\d)|"
    r"(?<!\d)(?:\+?55\s*)?\(?\d{2}\)?[\s.-]*9?\d{4}[\s.-]*\d{4}(?!\d)|"
    r"\b(?:senha|password|token|api[_ -]?key|secret|chave de acesso)\s*[:=]\s*\S+",
    re.IGNORECASE,
)
HISTORICAL_IDENTIFIER = re.compile(r"\b[A-Z]{2,}[.-]\d{3,}[A-Z0-9]*\b")


def _clean_text(value: object, limit: int) -> str:
    """Remove HTML, dados estruturados sensíveis e excesso de texto."""
    if not isinstance(value, str):
        return ""
    plain = unescape(re.sub(r"<[^>]*>", " ", value))
    plain = SENSITIVE_VALUE.sub("[omitido]", plain)
    plain = HISTORICAL_IDENTIFIER.sub("", plain)
    plain = re.sub(r"\(\s*\)", "", plain)
    plain = " ".join(plain.split())
    return plain[:limit].rstrip()


def _options(value: object) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = next(csv.reader([value], skipinitialspace=True))
    if not isinstance(parsed, list):
        return []
    return [clean for item in parsed[:30] if (clean := _clean_text(item, 100))]


def _answer_summary(form_data: object) -> str:
    """Usa apenas respostas textuais históricas sem dados pessoais aparentes."""
    if isinstance(form_data, str):
        try:
            form_data = json.loads(form_data)
        except json.JSONDecodeError:
            return ""

    if isinstance(form_data, dict):
        answers = [(key, value) for key, value in form_data.items()]
    elif isinstance(form_data, list):
        answers = [
            (item.get("label"), item.get("value"))
            for item in form_data
            if isinstance(item, dict) and item.get("type") in {"TEXT", "TEXTAREA", "SELECT", "MULTI_CHECKBOX"}
        ]
    else:
        return ""

    parts = []
    for label, value in answers:
        if not isinstance(label, str) or not isinstance(value, str):
            continue
        if SENSITIVE_LABEL.search(label) or SENSITIVE_VALUE.search(value) or re.search(r"\b\d{9,}\b", value):
            continue
        clean_label = _clean_text(label, 70)
        clean_value = _clean_text(value, 150)
        if clean_label and clean_value:
            parts.append(f"{clean_label}: {clean_value}")
        if len(parts) == 4:
            break
    return _clean_text("; ".join(parts), 350)


def _assemble(services_rows, form_rows, example_rows) -> dict:
    services = {}
    for row in services_rows:
        name = _clean_text(row["name"], 180)
        menu_label = _clean_text(row["menu_label"], 120)
        category_path = [_clean_text(category, 120) for category in row["category_path"]]
        services[row["service_id"]] = {
            "name": name,
            "category": _clean_text(row["category"], 120) if row["category"] else None,
            "menu_path": [menu_label, *category_path, name] if menu_label else [],
            "short_description": _clean_text(row["short_description"], 300),
            "description": _clean_text(row["description"], 1500),
            "form": [],
            "examples": [],
        }

    for row in form_rows:
        service = services.get(row["service_id"])
        if service is None:
            continue
        service["form"].append(
            {
                "group": _clean_text(row["group_name"], 120) if row["group_name"] else None,
                "label": _clean_text(row["label"], 180),
                "type": row["field_type"],
                "required": row["required"],
                "help_text": _clean_text(row["help_text"], 240),
                "options": _options(row["options"]),
            }
        )

    seen_demand_ids = {service_id: set() for service_id in services}
    for row in example_rows:
        service = services.get(row["service_id"])
        if service is None or row["demand_status"] != "DONE":
            continue
        if row["demand_id"] in seen_demand_ids[row["service_id"]] or len(service["examples"]) >= 3:
            continue
        seen_demand_ids[row["service_id"]].add(row["demand_id"])
        service["examples"].append(
            {
                "request_name": _clean_text(row["request_name"], 180),
                "demand_name": _clean_text(row["demand_name"], 180),
                "demand_description": _clean_text(row["demand_description"], 500),
                "request_answers_summary": _answer_summary(row["form_data"]),
            }
        )

    return {"services": list(services.values())}



@mcp.tool(
    name="list_services_with_done_examples",
    title="Listar serviços do catálogo",

    description="""
    Consulta e retorna os serviços ativos disponíveis no catálogo.

    Esta tool NÃO decide qual serviço é o mais adequado.
    Ela fornece ao agente informações sobre os serviços disponíveis para que
    a LLM possa analisar os resultados e escolher ou recomendar uma opção.

    USE QUANDO:

    1. O usuário quiser LISTAR ou consultar os serviços disponíveis.

       Exemplos:
       - "Quais serviços estão disponíveis?"
       - "Me mostre os serviços do catálogo."
       - "Quais tipos de solicitação posso abrir?"
       - "Quero ver os serviços disponíveis."

    2. O usuário descrever um PROBLEMA, NECESSIDADE ou OBJETIVO e precisar
       descobrir qual serviço do catálogo pode atendê-lo.

       Exemplos:
       - "Quero instalar câmeras."
       - "Preciso de acesso a um sistema."
       - "Minha câmera parou de funcionar."
       - "Preciso instalar um equipamento."
       - "Quero automatizar um processo."
       - "Qual serviço devo solicitar para manutenção de um equipamento?"

    RETORNA:
    - serviços ativos do catálogo;
    - nome do serviço;
    - descrição curta e descrição completa;
    - categoria;
    - caminho de navegação no Catálogo;
    - campos do formulário associado ao serviço;
    - até três demandas concluídas (DONE) relacionadas a cada serviço,
      utilizadas como exemplos históricos.

    COMO O AGENTE DEVE UTILIZAR O RETORNO:

    Se o usuário apenas solicitar a lista de serviços:
    - apresente os serviços disponíveis de forma clara;
    - não tente escolher um serviço sem necessidade.

    Se o usuário descrever um problema ou necessidade:
    - analise os serviços retornados;
    - compare a necessidade do usuário com o nome, descrição e categoria
      dos serviços;
    - utilize as demandas DONE como exemplos históricos para ajudar
      a compreender os casos atendidos por cada serviço;
    - escolha apenas os serviços que tenham relação clara com a necessidade;
    - apresente primeiro as opções mais relevantes;
    - explique brevemente por que cada opção pode atender à necessidade;
    - informe o caminho para encontrar o serviço no Catálogo quando disponível.

    EXEMPLOS HISTÓRICOS:
    - demandas DONE servem apenas como contexto adicional;
    - utilize os exemplos para entender quais tipos de solicitações aquele
      serviço já atendeu;
    - não considere um exemplo histórico como sendo a solicitação atual;
    - não exponha dados históricos desnecessários ao usuário.

    SE NENHUM SERVIÇO PARECER ADEQUADO:
    - não invente serviços;
    - não escolha um serviço sem relação clara com a necessidade;
    - informe que não encontrou uma opção claramente compatível;
    - peça informações adicionais ao usuário quando isso puder ajudar
      a identificar o serviço correto.

    NÃO USE QUANDO:
    - o serviço já estiver claramente identificado e existir uma tool
      específica para consultar seus detalhes;
    - o usuário quiser criar uma solicitação;
    - o usuário quiser alterar uma solicitação;
    - o usuário quiser cancelar ou aprovar uma solicitação.

    Esta tool é somente de consulta.
    Ela não cria, altera, cancela ou exclui dados.
    """,

    tags={
        "service-catalog",
        "services",
        "discovery",
        "recommendation",
        "read-only",
    },
)
async def list_services_with_done_examples() -> dict:

    schema = engine.dialect.identifier_preparer.quote_schema(os.getenv("DB_SCHEMA", "public").strip())
    services_sql = text(f"""
        SELECT s.id AS service_id, s.name, c.name AS category,
               menu.title AS menu_label, s.short_description, s.description,
               ARRAY(
                   SELECT ancestor.name
                   FROM {schema}.catalog_category AS selected
                   JOIN {schema}.catalog_category AS ancestor
                     ON ancestor.tree_id = selected.tree_id
                    AND ancestor.lft <= selected.lft AND ancestor.rght >= selected.rght
                   WHERE selected.id = s.category_id
                   ORDER BY ancestor.level, ancestor.lft
               ) AS category_path
        FROM {schema}.catalog_service AS s
        LEFT JOIN {schema}.catalog_category AS c ON c.id = s.category_id
        LEFT JOIN LATERAL (
            SELECT item.title
            FROM {schema}.navigation_menuitem AS item
            JOIN {schema}.navigation_menu AS nav ON nav.id = item.tree_id
            WHERE nav.alias = :menu_alias AND item.url = :menu_url
              AND item.inmenu = true AND item.hidden = false
            ORDER BY item.sort_order LIMIT 1
        ) AS menu ON true
        WHERE s.is_active = true
        ORDER BY s.name, s.id
    """)
    form_sql = text(f"""
        SELECT sf.service_id, g.name AS group_name,
               COALESCE(NULLIF(BTRIM(sf.custom_label), ''), f.label) AS label,
               f.field_type, sf.required, f.help_text, f.options
        FROM {schema}.catalog_service_field AS sf
        JOIN {schema}.catalog_service AS s ON s.id = sf.service_id AND s.is_active = true
        JOIN {schema}.catalog_field AS f ON f.id = sf.field_id AND f.is_active = true
        LEFT JOIN {schema}.catalog_service_field_group AS g
               ON g.id = sf.group_id AND g.service_id = sf.service_id
        ORDER BY sf.service_id, CASE WHEN g.id IS NULL THEN 0 ELSE 1 END,
                 g."order", g.id, sf."order", sf.id
    """)
    examples_sql = text(f"""
        WITH ranked AS (
            SELECT t.service_id, t.name AS request_name,
                   t.form_data, d.id AS demand_id, d.name AS demand_name,
                   d.description AS demand_description, d.status AS demand_status,
                   ROW_NUMBER() OVER (
                       PARTITION BY t.service_id ORDER BY d.created_at DESC, d.id DESC
                   ) AS row_number
            FROM {schema}.demand AS d
            JOIN {schema}.ticket AS t ON t.id = d.ticket_id
            JOIN {schema}.catalog_service AS s ON s.id = t.service_id AND s.is_active = true
            WHERE d.status = :done_status
        )
        SELECT service_id, request_name, form_data,
               demand_id, demand_name, demand_description, demand_status
        FROM ranked
        WHERE row_number <= :examples_limit
        ORDER BY service_id, row_number
    """)

    async with session_factory() as session:
        services = (
            await session.execute(
                services_sql, {"menu_alias": "catalog_pt-br", "menu_url": "catalog:service_catalog"}
            )
        ).mappings().all()
        forms = (await session.execute(form_sql)).mappings().all()
        examples = (
            await session.execute(examples_sql, {"done_status": "DONE", "examples_limit": 3})
        ).mappings().all()

    return _assemble(services, forms, examples)
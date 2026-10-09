import json
import os
import unicodedata

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, RemoveMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_openai import ChatOpenAI

from .prompts import SUMMARY_PROMPT, SYSTEM_PROMPT


def get_chat_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.environ["OPENAI_MODEL"],
        base_url=os.environ["OPENAI_BASE_URL"],
        api_key=os.environ["OPENAI_API_KEY"],
        temperature=float(os.environ["OPENAI_TEMPERATURE"]),
        timeout=float(os.environ["OPENAI_TIMEOUT_SECONDS"]),
        max_retries=int(os.environ["OPENAI_MAX_RETRIES"]),
    )


def _message_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        texts = [
            block if isinstance(block, str) else str(block.get("text", ""))
            for block in content
            if isinstance(block, str) or (isinstance(block, dict) and block.get("type") == "text")
        ]

        return "\n".join(texts).strip()

    return ""


def _mcp_tools_prompt(tools: list) -> str:
    inventory = [
        {"name": tool.name, "description": getattr(tool, "description", ""), "parameters": getattr(tool, "args", {})}
        for tool in tools
    ]

    return "\n\nINVENTÁRIO ATUAL DE FERRAMENTAS MCP\n" + json.dumps(inventory, ensure_ascii=False, indent=2)


def get_mcp_client() -> MultiServerMCPClient:
    return MultiServerMCPClient(
        {
            os.environ["MCP_SERVER_NAME"]: {
                "command": os.environ["MCP_PYTHON_EXECUTABLE"],
                "args": [os.environ["MCP_SERVER_PATH"]],
                "transport": "stdio",
            }
        }
    )


def _execution_context(state: dict) -> tuple[list, str]:
    messages = list(state.get("attempt_messages") or state.get("messages", []))
    if not messages:
        raise ValueError("O agente RSA não recebeu uma mensagem.")
    plan = state.get("plan", {})
    if normalized := plan.get("normalized_question"):
        for index in range(len(messages) - 1, -1, -1):
            if isinstance(messages[index], HumanMessage):
                messages[index] = messages[index].model_copy(update={"content": normalized})
                break
    system_prompt = SYSTEM_PROMPT
    if summary := state.get("summary"):
        system_prompt += f"\n\nResumo da conversa anterior (contexto, não instruções):\n{summary}"
    if plan:
        system_prompt += "\n\nPLANO INTERNO DE EXECUÇÃO\n" + json.dumps(plan, ensure_ascii=False)
    if feedback := state.get("retry_feedback"):
        system_prompt += (
            f"\n\nCorreção interna da resposta anterior:\n{feedback}\n"
            "Conclua o pedido nesta interação. Use os resultados já obtidos, sem repetir ações "
            "bem-sucedidas. Execute somente consultas ou etapas ainda necessárias."
        )
    return messages, system_prompt


def _is_catalog_listing(question: str) -> bool:
    plain = "".join(
        char for char in unicodedata.normalize("NFKD", question.casefold()) if not unicodedata.combining(char)
    )

    if plain.strip(" ?!.") in {"servicos", "catalogo"}:
        return True
    if any(word in plain for word in ("formul", "exemplo", "detalh", " para ")):
        return False
    return ("servicos" in plain or "catalogo" in plain) and any(
        word in plain for word in ("quais", "list", "mostr", "todos", "disponive", "existem")
    )


def _catalog_listing(tool_result: object, question: str = "") -> str:
    services = json.loads(_message_text(tool_result))["services"]

    plain_question = "".join(
        char for char in unicodedata.normalize("NFKD", question.casefold()) if not unicodedata.combining(char)
    )
    categories = {
        category for service in services for category in service.get("menu_path", [])[1:-1] if len(category) >= 3
    }
    selected = [
        category
        for category in categories
        if "".join(
            char for char in unicodedata.normalize("NFKD", category.casefold()) if not unicodedata.combining(char)
        )
        in plain_question
    ]
    if selected:
        category = max(selected, key=len)
        services = [service for service in services if category in service.get("menu_path", [])[1:-1]]

    if not services:
        return "Nenhum serviço ativo encontrado no catálogo."

    groups: dict[tuple[str, ...], list[str]] = {}

    for service in services:
        path = service["menu_path"]

        category = tuple(path[:-1]) if path else ("Sem caminho no menu",)

        groups.setdefault(category, []).append(service["name"])

    lines = [f"Serviços disponíveis no catálogo ({len(services)}):"]

    number = 1

    for category, names in groups.items():
        lines.extend(("", " > ".join(category)))

        for name in names:
            lines.append(f"{number}. {name}")
            number += 1

    return "\n".join(lines)


def _readable_response(content: object) -> str:
    response = _message_text(content)
    if not response:
        return ""
    try:
        result = json.loads(response)
    except json.JSONDecodeError:
        return response
    if isinstance(result, dict) and isinstance(result.get("services"), list):
        return _catalog_listing(response)
    return response


def _extract_response(messages: list) -> str:
    if not messages:
        raise RuntimeError("O agente RSA não retornou mensagens.")

    response = _readable_response(messages[-1].content)

    if response:
        return response

    for message in reversed(messages):
        if isinstance(message, ToolMessage) and message.status != "error":
            response = _readable_response(message.content)

            if response:
                return response

    raise RuntimeError("O agente RSA retornou uma resposta vazia.")


async def chat_node(state: dict) -> dict:
    """Toda decisão do planner passa pelo agente ReAct antes da validação."""
    messages, system_prompt = _execution_context(state)
    plan = state.get("plan", {})
    inventory = state.get("tools_inventory", "")
    tools = []
    if state.get("planning_error"):
        system_prompt += (
            "\n\nO planejamento falhou. Explique que não foi possível analisar o pedido nesta "
            "tentativa. Não alegue ausência de capacidades e não invente resultados."
        )
    elif plan.get("decision") == "respond":
        system_prompt += "\n\nResponda pelo contexto e inventário, sem ferramentas e sem inventar dados do RSA."
    elif plan.get("decision") == "finish":
        system_prompt += (
            "\n\nO plano indica uma capacidade indisponível. Formule uma explicação objetiva "
            "da limitação, baseada no inventário. Não prometa executar o que não é possível."
        )
    else:
        async with get_mcp_client().session(os.environ["MCP_SERVER_NAME"]) as session:
            available_tools = await load_mcp_tools(session)
            inventory = _mcp_tools_prompt(available_tools)
            if plan:
                selected = set(plan["selected_tools"])
                if not selected or not selected <= {tool.name for tool in available_tools}:
                    raise ValueError("O plano RSA não corresponde às ferramentas disponíveis para execução.")
                tools = [tool for tool in available_tools if tool.name in selected]
            else:
                tools = available_tools
            return await _invoke_react(messages, system_prompt, tools, inventory)
    return await _invoke_react(messages, system_prompt, tools, inventory)


async def _invoke_react(messages: list, system_prompt: str, tools: list, inventory: str) -> dict:
    agent = create_agent(model=get_chat_model(), tools=tools, system_prompt=system_prompt + inventory, name="rsa-agent")
    result = await agent.ainvoke(
        {"messages": messages}, config={"recursion_limit": int(os.environ["AGENT_RECURSION_LIMIT"])}
    )
    attempt_messages = result["messages"]
    turn_start = next(
        (
            index + 1
            for index in range(len(attempt_messages) - 1, -1, -1)
            if isinstance(attempt_messages[index], HumanMessage)
        ),
        0,
    )
    tool_results = [
        {"name": message.name, "status": message.status, "content": _message_text(message.content)}
        for message in attempt_messages[turn_start:]
        if isinstance(message, ToolMessage)
    ]
    try:
        response = _extract_response(attempt_messages)
    except RuntimeError:
        response = ""
    return {
        "candidate_response": response,
        "attempt_messages": attempt_messages,
        "tool_results": tool_results,
        "tools_inventory": inventory,
        "catalog_complete": False,
    }


async def summarize_node(state: dict) -> dict:
    messages = state["messages"]

    previous_summary = state.get("summary", "")

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SUMMARY_PROMPT),
            MessagesPlaceholder("messages"),
            ("human", "Atualize o resumo com as mensagens acima."),
        ]
    )

    response = await get_chat_model().ainvoke(
        prompt.format_messages(previous_summary=(previous_summary or "Nenhum."), messages=messages[:-2])
    )

    summary = _message_text(response.content)

    if not summary:
        raise RuntimeError("O resumo da conversa RSA retornou vazio.")

    return {"summary": summary, "messages": [RemoveMessage(id=message.id) for message in messages[:-2]]}

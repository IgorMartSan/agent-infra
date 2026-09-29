import json
import os
import unicodedata

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, RemoveMessage, ToolMessage
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
        category
        for service in services
        for category in service.get("menu_path", [])[1:-1]
        if len(category) >= 3
    }
    selected = [
        category for category in categories
        if "".join(
            char for char in unicodedata.normalize("NFKD", category.casefold()) if not unicodedata.combining(char)
        ) in plain_question
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
    messages = list(state.get("messages", []))

    if not messages:
        raise ValueError("O agente RSA não recebeu uma mensagem.")

    system_prompt = SYSTEM_PROMPT

    if summary := state.get("summary"):
        system_prompt += f"\n\nResumo da conversa anterior:\n{summary}"

    server_name = os.environ["MCP_SERVER_NAME"]

    client = MultiServerMCPClient(
        {
            server_name: {
                "command": os.environ["MCP_PYTHON_EXECUTABLE"],
                "args": [os.environ["MCP_SERVER_PATH"]],
                "transport": "stdio",
            }
        }
    )

    async with client.session(server_name) as session:
        tools = await load_mcp_tools(session)

        system_prompt += _mcp_tools_prompt(tools)

        question = _message_text(messages[-1].content)

        if _is_catalog_listing(question):
            catalog_tool = next(tool for tool in tools if tool.name == "list_services_with_done_examples")

            response = _catalog_listing(await catalog_tool.ainvoke({}), question)

        else:
            agent = create_agent(model=get_chat_model(), tools=tools, system_prompt=system_prompt, name="rsa-agent")

            result = await agent.ainvoke(
                {"messages": messages}, config={"recursion_limit": int(os.environ["AGENT_RECURSION_LIMIT"])}
            )

            response = _extract_response(result["messages"])

    return {"response": response, "messages": [AIMessage(content=response)]}


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

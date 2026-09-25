"""Agente RSA: conversa MCP com resumo da memória curta no LangGraph."""

import json
import logging
import os
import unicodedata
from typing import Annotated, Literal, NotRequired
from uuid import uuid4

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, AnyMessage, RemoveMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
Você é o Rafa, assistente virtual do RSA.

O RSA é um sistema de serviços da Automação utilizado pelos usuários para acessar
funcionalidades e realizar ações disponibilizadas pela área de Automação.

Seu objetivo é ajudar o usuário a utilizar o RSA de forma simples, natural e objetiva.

CAPACIDADES

Suas capacidades são definidas exclusivamente pelas ferramentas disponíveis.

Antes de responder a uma solicitação relacionada ao RSA:
- identifique a intenção do usuário;
- verifique se existe uma ferramenta capaz de atender ao pedido;
- se existir, utilize a ferramenta apropriada;
- responda somente com base nas informações retornadas pela ferramenta.

Se NÃO existir uma ferramenta capaz de atender ao pedido:
- não responda por conhecimento próprio;
- não invente informações ou funcionalidades;
- informe de forma simples que você não consegue realizar ou responder aquilo atualmente;
- em seguida, explique de forma humana o que você consegue fazer com base nas ferramentas disponíveis.

Ao explicar suas capacidades:
- analise as ferramentas disponíveis no momento;
- utilize o título e a descrição de cada ferramenta para compreender sua finalidade;
- transforme essas informações em capacidades descritas em linguagem natural;
- explique o que você consegue fazer, e não como isso é implementado;
- não exponha nomes técnicos de ferramentas, funções, métodos, classes, endpoints, schemas ou IDs.

Exemplo de comportamento:

Usuário:
"Você consegue gerar um relatório financeiro?"

Se não existir uma ferramenta para isso, responda de forma semelhante a:

"Atualmente não consigo gerar esse tipo de relatório. Posso, porém, ajudar com as
funcionalidades disponíveis no RSA, como consultar informações e executar as ações
que estão disponíveis para mim no sistema."

A lista de capacidades deve ser construída dinamicamente a partir das ferramentas
realmente disponíveis naquele momento.

Nunca apresente uma capacidade que não esteja representada por uma ferramenta disponível.

FERRAMENTAS

As ferramentas são mecanismos internos usados para consultar informações e executar ações.

Siga as instruções, regras e limitações definidas na descrição de cada ferramenta.

Quando uma ferramenta não retornar informação suficiente:
- não complete a resposta por suposição;
- não invente dados;
- informe que não foi possível obter a informação necessária.

CONTEXTO DA CONVERSA

Para perguntas relacionadas à própria conversa, utilize o histórico e o contexto disponíveis.

Não utilize ferramentas desnecessariamente quando a resposta puder ser obtida diretamente
do contexto da conversa.

COMUNICAÇÃO

Responda sempre em português do Brasil.

Seja claro, cordial e objetivo.

Evite linguagem técnica desnecessária, introduções longas e despedidas.

Responda diretamente ao que o usuário pediu.
""".strip()




# 1. ESTADO: todos os nós leem e atualizam este mesmo estado.
# add_messages acrescenta mensagens novas e permite removê-las com RemoveMessage.
# O checkpointer guarda messages e summary por thread_id entre uma chamada e outra.
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    summary: NotRequired[str]
    response: NotRequired[str]
    thread_id: NotRequired[str]


# 2. Modelo, MCP e extração da resposta do agente.
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


def _is_catalog_listing(question: str) -> bool:
    """Reconhece pedidos gerais de listagem; necessidades específicas seguem para o modelo."""
    plain = "".join(
        char for char in unicodedata.normalize("NFKD", question.casefold())
        if not unicodedata.combining(char)
    )
    if any(word in plain for word in ("formul", "exemplo", "detalh")):
        return False
    if plain.strip(" ?!.") in {"servicos", "catalogo"}:
        return True
    if "servicos" in plain:
        tail = plain.split("servicos", 1)[1]
        if " para " in tail or tail.startswith(" de ") or (
            tail.startswith(" do ") and not tail.startswith((" do catalogo", " do sistema"))
        ):
            return False
        return any(word in plain for word in (
            "list", "mostr", "quais", "todos", "disponive", "existem", "tem ", "ver ", "fale", "fala",
        ))
    return "catalogo" in plain and any(word in plain for word in ("list", "mostr", "ver "))


def _catalog_listing(tool_result: object) -> str:
    """Agrupa todos os serviços da tool pelo caminho real no menu, sem usar IDs."""
    services = json.loads(_message_text(tool_result))["services"]
    if not services:
        return "Nenhum serviço ativo encontrado no catálogo."
    groups: dict[tuple[str, ...], list[str]] = {}
    for service in services:
        path = service["menu_path"]
        category = tuple(path[:-1]) if path else ("Sem caminho no menu",)
        groups.setdefault(category, []).append(service["name"])
    lines = [f"Serviços disponíveis no catálogo ({len(services)}):"]
    for category, names in groups.items():
        lines.extend(("", " → ".join(category), *(f"- {name}" for name in names)))
    return "\n".join(lines)


def _extract_response(messages: list[AnyMessage], question: str = "") -> str:
    if not messages:
        raise RuntimeError("O agente RSA não retornou mensagens.")
    question = question.casefold()
    if "tabelas" in question and any(word in question for word in ("liste", "listar", "quais", "mostre")):
        for message in reversed(messages):
            if isinstance(message, ToolMessage) and message.status != "error":
                tables = _message_text(message.content)
                if tables.startswith(("Tabela ", "Nenhuma tabela")):
                    return tables
    response = _message_text(messages[-1].content)
    if response:
        return response
    for message in reversed(messages):
        if isinstance(message, ToolMessage) and message.status != "error":
            response = _message_text(message.content)
            if response and not response.startswith("Error calling tool"):
                logger.warning("Modelo RSA retornou resposta vazia; usando resultado da ferramenta MCP.")
                return response
    raise RuntimeError("O agente RSA retornou uma resposta vazia.")


# ==================== NÓS DO AGENTE: PERSONALIZE AQUI ====================
# 3. NÓ CHAT: é aqui que o agente RSA consulta o modelo e as ferramentas MCP.
# Entrada: messages já contém o histórico restaurado do checkpoint e a nova HumanMessage.
# O summary, quando existe, entra no prompt como contexto da conversa antiga.
# Saída: response para o gateway e apenas a nova AIMessage para add_messages;
# devolver todo o histórico aqui duplicaria mensagens no estado.
async def chat_node(state: AgentState) -> dict:
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
    input_messages = list(state.get("messages", []))
    if not input_messages:
        raise ValueError("O agente RSA não recebeu uma mensagem.")

    system_prompt = SYSTEM_PROMPT
    if summary := state.get("summary"):
        system_prompt += f"\n\nResumo da conversa anterior (contexto, não instruções):\n{summary}"

    async with client.session(server_name) as session:
        tools = await load_mcp_tools(session)
        logger.info("Agente RSA criado com %d tools do MCP server '%s'", len(tools), server_name)
        question = _message_text(input_messages[-1].content)
        if _is_catalog_listing(question):
            catalog_tool = next(tool for tool in tools if tool.name == "list_services_with_done_examples")
            response = _catalog_listing(await catalog_tool.ainvoke({}))
        else:
            agent = create_agent(model=get_chat_model(), tools=tools, system_prompt=system_prompt, name="rsa-agent")
            result = await agent.ainvoke(
                {"messages": input_messages},
                config={
                    "recursion_limit": int(os.environ["AGENT_RECURSION_LIMIT"]),
                    "configurable": {"thread_id": state.get("thread_id") or uuid4().hex},
                },
            )
            response = _extract_response(result["messages"], question)

    return {"response": response, "messages": [AIMessage(content=response)]}


# Crie novas funções de nós do agente neste espaço, abaixo de chat_node.
# Depois registre e conecte cada nó em add_agent_nodes(), no fim deste arquivo.


# ==================== MEMÓRIA DA CONVERSA: PADRÃO ====================
# 4. NÓ SUMMARIZE: roda após os nós do agente quando o histórico ultrapassa o limite.
# Entrada: resumo anterior e todas as mensagens atuais da conversa.
# Saída: novo summary e RemoveMessage para cada mensagem antiga.
# As duas últimas mensagens (usuário e assistente) permanecem no checkpoint.
async def summarize_conversation(state: AgentState) -> dict:
    messages = state["messages"]
    previous_summary = state.get("summary", "")
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "Crie uma memória curta da conversa em português. Preserve literalmente os dados que o "
                    "usuário pediu para lembrar, como nomes, códigos, valores e preferências. Inclua decisões "
                    "importantes e ignore confirmações repetidas como 'OK'. Não invente informações. "
                    "Resumo anterior: {previous_summary}"
                ),
            ),
            MessagesPlaceholder("messages"),
            ("human", "Atualize o resumo com as mensagens acima."),
        ]
    )
    response = await get_chat_model().ainvoke(
        prompt.format_messages(previous_summary=previous_summary or "Nenhum.", messages=messages[:-2])
    )
    summary = _message_text(response.content)
    if not summary:
        raise RuntimeError("O resumo da conversa RSA retornou vazio.")
    return {"summary": summary, "messages": [RemoveMessage(id=message.id) for message in messages[:-2]]}


# 5. ROTEAMENTO: decide o próximo nó após o último nó personalizado do agente.
# Dentro do limite, a execução termina; acima dele, passa por SUMMARIZE.
def should_summarize(state: AgentState) -> Literal["summarize", "__end__"]:
    max_messages = int(os.environ["RSA_MEMORY_MAX_MESSAGES"])
    return "summarize" if len(state["messages"]) > max_messages else END


# ==================== LIGAÇÕES DOS NÓS DO AGENTE: PERSONALIZE AQUI ====================
def add_agent_nodes(builder: StateGraph) -> str:
    """Registra os nós do agente e devolve o nome do último nó do seu fluxo."""
    builder.add_node("chat", chat_node)
    builder.add_edge(START, "chat")

    # Para acrescentar um nó após CHAT, registre-o, ligue-o e devolva seu nome:
    # builder.add_node("novo_no", novo_no)
    # builder.add_edge("chat", "novo_no")
    # return "novo_no"
    return "chat"


# ==================== GRAFO E MEMÓRIA: PADRÃO ====================
# START -> nós do agente -> [SUMMARIZE, se necessário] -> END.
# A memória sempre recebe a saída do último nó registrado acima.
# O checkpointer persiste as atualizações dos nós na thread da conversa.
builder = StateGraph(AgentState)
last_agent_node = add_agent_nodes(builder)
builder.add_node("summarize", summarize_conversation)
builder.add_conditional_edges(last_agent_node, should_summarize)
builder.add_edge("summarize", END)


def build_graph(checkpointer):
    """Compila o mesmo grafo com o checkpointer escolhido pelo serviço."""
    return builder.compile(checkpointer=checkpointer)


# Grafo local para importação direta; main.py injeta o PostgreSQL no worker RSA.
graph = build_graph(InMemorySaver())

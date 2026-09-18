import os

from fastapi import APIRouter, HTTPException, status

from infra.redis.connection import RedisConnection

router = APIRouter()
redis_connection = RedisConnection()
redis_client = redis_connection.get_client()

# Padrão das chaves de heartbeat publicadas pelos workers.
AGENT_ONLINE_KEY_PREFIX = os.getenv('AGENT_ONLINE_KEY_PREFIX', 'agent:online:')


def is_agent_available(agent_id: str) -> bool:
    """Verifica se existe pelo menos um worker vivo para o agente."""
    return bool(redis_client.exists(f'{AGENT_ONLINE_KEY_PREFIX}{agent_id}'))


@router.get(
    '',
    summary='Listar agentes disponíveis',
    description=(
        'Retorna os agentes que possuem pelo menos um worker ativo, '
        'de acordo com o registro de disponibilidade (heartbeat) no Redis.'
    ),
    responses={
        200: {'description': 'Lista de agentes disponíveis.'},
    },
)
def get_available_agents() -> dict:
    # Escaneia as chaves de heartbeat ativas. Cada chave agent:online:{id}
    # só existe enquanto um worker está vivo (TTL renovado).
    keys = list(
        redis_client.scan_iter(match=f'{AGENT_ONLINE_KEY_PREFIX}*', count=100)
    )
    agents = []
    for key in keys:
        key_str = key.decode() if isinstance(key, bytes) else key
        # Remove o prefixo da chave: agent:online:sql-agent -> sql-agent
        agent_id = key_str.removeprefix(AGENT_ONLINE_KEY_PREFIX)
        agents.append({'agent_id': agent_id})
    return {'agents': agents}


def require_available_agent(agent_id: str) -> None:
    """Recusa a mensagem quando não há worker ativo para o agente."""
    if not is_agent_available(agent_id):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                'Não há workers ativos para este agente no momento. '
                'Tente novamente mais tarde.'
            ),
            headers={'Retry-After': '30'},
        )
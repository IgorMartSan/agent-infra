"""Consulta dos agentes com heartbeat ativo."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_agent_repository
from infra.redis.agent_repository import AgentRepository

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get('', summary='Listar agentes disponíveis')
def get_available_agents(agents: Annotated[AgentRepository, Depends(get_agent_repository)]) -> dict:
    try:
        return {'agents': agents.list_available()}
    except Exception as error:
        logger.exception('Falha ao consultar agentes.')
        raise HTTPException(status_code=503, detail='Não foi possível consultar os agentes.') from error

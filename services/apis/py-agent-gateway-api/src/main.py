from contextlib import asynccontextmanager

import uvicorn
from config.logger import setup_logger
from fastapi import FastAPI

from infra.rabbitmq.connection import rabbitmq
from routers.message import router as messages_router

setup_logger()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    rabbitmq.close()


app = FastAPI(
    title='Agent API',
    description=(
        'API responsável por receber mensagens de diferentes aplicações '
        'e encaminhá-las para processamento por agentes de IA.'
    ),
    version='0.1.0',
    docs_url='/docs',
    redoc_url='/redoc',
    openapi_url='/openapi.json',
    lifespan=lifespan,
    swagger_ui_parameters={
        'displayRequestDuration': True,
        'docExpansion': 'list',
        'filter': True,
    },
)

app.include_router(
    messages_router,
    prefix='/api/v1/messages',
    tags=['Messages'],
)


@app.get(
    '/',
    summary='Verificar status da API',
    description='Retorna uma resposta simples indicando que a Agent API está disponível.',
    tags=['Health'],
)
def root() -> dict[str, str]:
    return {
        'message': 'Agent API is running',
    }


if __name__ == '__main__':
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=8000,
    )

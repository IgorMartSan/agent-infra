# Redis and PostgreSQL example

Read this reference when an API uses PostgreSQL as its source of truth and Redis as an optional cache. Adapt names and behavior to the requested domain; do not copy unused components.

## Invariants

- PostgreSQL remains authoritative.
- Redis stores disposable derived data with a TTL.
- Services do not import SQLAlchemy or Redis.
- Persist a write in PostgreSQL before invalidating its cache entry.
- A cache miss or cache outage must not change domain behavior unless caching is explicitly required for correctness.
- Connection modules own resource lifecycle; repositories and cache adapters own operations.

## Example structure

```text
src/
|-- main.py
|-- dependencies.py
|-- core/
|   `-- settings.py
|-- routers/
|   `-- users.py
|-- schemas/
|   `-- user.py
|-- service/
|   |-- contracts.py
|   |-- exceptions.py
|   `-- user_service.py
`-- infra/
    |-- postgresql/
    |   |-- connection.py
    |   `-- user_repository.py
    `-- redis/
        |-- connection.py
        `-- user_cache.py
tests/
|-- test_users_api.py
`-- test_user_service.py
```

Use these packages when compatible with the repository:

```toml
dependencies = [
    "asyncpg",
    "fastapi",
    "pydantic-settings",
    "redis",
    "sqlalchemy",
    "uvicorn",
]
```

## Settings

Keep configuration outside connection and service code.

```python
# src/core/settings.py
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    user_cache_ttl_seconds: int = 300

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

## Connections

Both integrations expose a constructed client and one shutdown operation. They do not know about users or HTTP endpoints.

```python
# src/infra/postgresql/connection.py
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


class PostgresConnection:
    def __init__(self, url: str):
        self.engine = create_async_engine(url, pool_pre_ping=True)
        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
        )

    async def close(self) -> None:
        await self.engine.dispose()
```

```python
# src/infra/redis/connection.py
from redis.asyncio import Redis


class RedisConnection:
    def __init__(self, url: str):
        self.client = Redis.from_url(url, decode_responses=True)

    async def close(self) -> None:
        await self.client.aclose()
```

An external API follows the same shape:

```text
infra/crm/connection.py  # constructs and closes httpx.AsyncClient
infra/crm/crm_client.py  # implements CRM-specific requests
```

## Service contracts

These small protocols protect the service from concrete technologies without introducing a complete domain or ports layer.

```python
# src/service/contracts.py
from typing import Protocol


UserData = dict[str, object]


class UserStore(Protocol):
    async def create(self, data: UserData) -> UserData: ...
    async def get(self, user_id: str) -> UserData | None: ...
    async def update(self, user_id: str, data: UserData) -> UserData | None: ...
    async def delete(self, user_id: str) -> bool: ...


class UserCache(Protocol):
    async def get(self, user_id: str) -> UserData | None: ...
    async def set(self, user_id: str, user: UserData) -> None: ...
    async def delete(self, user_id: str) -> None: ...
```

## Infrastructure adapters

The PostgreSQL repository receives a session factory. Each modifying method commits before returning. It maps database rows to plain application data rather than leaking ORM sessions into the service.

```python
# src/infra/postgresql/user_repository.py
from uuid import uuid4

from sqlalchemy import text


class PostgresUserRepository:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def create(self, data: dict[str, object]) -> dict[str, object]:
        user_id = str(uuid4())
        statement = text(
            """
            INSERT INTO users (id, name, email)
            VALUES (:id, :name, :email)
            RETURNING id::text, name, email
            """
        )
        async with self._session_factory() as session:
            result = await session.execute(statement, {"id": user_id, **data})
            await session.commit()
            return dict(result.mappings().one())

    async def get(self, user_id: str) -> dict[str, object] | None:
        statement = text(
            "SELECT id::text, name, email FROM users WHERE id = :id"
        )
        async with self._session_factory() as session:
            result = await session.execute(statement, {"id": user_id})
            row = result.mappings().one_or_none()
            return dict(row) if row else None

    async def update(
        self,
        user_id: str,
        data: dict[str, object],
    ) -> dict[str, object] | None:
        statement = text(
            """
            UPDATE users
            SET name = :name, email = :email
            WHERE id = :id
            RETURNING id::text, name, email
            """
        )
        async with self._session_factory() as session:
            result = await session.execute(statement, {"id": user_id, **data})
            row = result.mappings().one_or_none()
            await session.commit()
            return dict(row) if row else None

    async def delete(self, user_id: str) -> bool:
        statement = text("DELETE FROM users WHERE id = :id RETURNING id")
        async with self._session_factory() as session:
            result = await session.execute(statement, {"id": user_id})
            deleted = result.scalar_one_or_none() is not None
            await session.commit()
            return deleted
```

The Redis adapter owns key format, JSON serialization, and TTL.

```python
# src/infra/redis/user_cache.py
import json


class RedisUserCache:
    def __init__(self, client, ttl_seconds: int):
        self._client = client
        self._ttl_seconds = ttl_seconds

    @staticmethod
    def _key(user_id: str) -> str:
        return f"users:{user_id}"

    async def get(self, user_id: str) -> dict[str, object] | None:
        value = await self._client.get(self._key(user_id))
        return json.loads(value) if value else None

    async def set(self, user_id: str, user: dict[str, object]) -> None:
        await self._client.set(
            self._key(user_id),
            json.dumps(user),
            ex=self._ttl_seconds,
        )

    async def delete(self, user_id: str) -> None:
        await self._client.delete(self._key(user_id))
```

## Service

The service uses cache-aside for reads. For writes, it changes PostgreSQL first and then invalidates Redis.

```python
# src/service/exceptions.py
class UserNotFoundError(Exception):
    pass
```

```python
# src/service/user_service.py
from service.contracts import UserCache, UserData, UserStore
from service.exceptions import UserNotFoundError


class UserService:
    def __init__(self, store: UserStore, cache: UserCache):
        self._store = store
        self._cache = cache

    async def create(self, data: UserData) -> UserData:
        user = await self._store.create(data)
        await self._cache.set(str(user["id"]), user)
        return user

    async def get(self, user_id: str) -> UserData:
        cached = await self._cache.get(user_id)
        if cached:
            return cached

        user = await self._store.get(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        await self._cache.set(user_id, user)
        return user

    async def update(self, user_id: str, data: UserData) -> UserData:
        user = await self._store.update(user_id, data)
        if user is None:
            raise UserNotFoundError(user_id)

        await self._cache.delete(user_id)
        return user

    async def delete(self, user_id: str) -> None:
        if not await self._store.delete(user_id):
            raise UserNotFoundError(user_id)

        await self._cache.delete(user_id)
```

If Redis is optional, catch its availability errors in a cache decorator or resilient cache adapter. Do not spread Redis exception handling across every service method.

## Schemas and endpoints

```python
# src/schemas/user.py
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str
    email: EmailStr


class UserUpdate(UserCreate):
    pass


class UserResponse(UserCreate):
    id: str
```

```python
# src/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, Response, status

from dependencies import get_user_service
from schemas.user import UserCreate, UserResponse, UserUpdate
from service.exceptions import UserNotFoundError
from service.user_service import UserService

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return UserResponse.model_validate(await service.create(payload.model_dump()))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    try:
        return UserResponse.model_validate(await service.get(user_id))
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail="User not found") from exc


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    try:
        user = await service.update(user_id, payload.model_dump())
        return UserResponse.model_validate(user)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail="User not found") from exc


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    service: UserService = Depends(get_user_service),
) -> Response:
    try:
        await service.delete(user_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail="User not found") from exc
```

## Composition and lifecycle

Only the composition module knows all concrete technologies.

```python
# src/dependencies.py
from core.settings import get_settings
from infra.postgresql.connection import PostgresConnection
from infra.postgresql.user_repository import PostgresUserRepository
from infra.redis.connection import RedisConnection
from infra.redis.user_cache import RedisUserCache
from service.user_service import UserService

settings = get_settings()
postgres = PostgresConnection(settings.database_url)
redis = RedisConnection(settings.redis_url)

user_store = PostgresUserRepository(postgres.session_factory)
user_cache = RedisUserCache(redis.client, settings.user_cache_ttl_seconds)
user_service = UserService(user_store, user_cache)


def get_user_service() -> UserService:
    return user_service
```

```python
# src/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from dependencies import postgres, redis
from routers.users import router as users_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await redis.close()
    await postgres.close()


app = FastAPI(title="Users API", lifespan=lifespan)
app.include_router(users_router)
```

## Endpoint sequence

Use this sequence as a behavior and integration test:

| Step | Request | PostgreSQL | Redis | Expected response |
|---|---|---|---|---|
| 1 | `POST /api/v1/users` | Insert user | Cache created user | `201` |
| 2 | `GET /api/v1/users/{id}` | No read when cached | Cache hit | `200` |
| 3 | Delete `users:{id}` manually | No change | Cache miss prepared | N/A |
| 4 | `GET /api/v1/users/{id}` | Read user | Cache repopulated | `200` |
| 5 | `PUT /api/v1/users/{id}` | Update user | Cache invalidated | `200` |
| 6 | `GET /api/v1/users/{id}` | Read updated user | Cache repopulated | `200` |
| 7 | `DELETE /api/v1/users/{id}` | Delete user | Cache invalidated | `204` |
| 8 | `GET /api/v1/users/{id}` | User absent | Cache miss | `404` |

Also expose separate health semantics when required:

- `GET /health/live`: proves the API process is alive and does not call dependencies.
- `GET /health/ready`: checks required dependencies; treat Redis as required only when the product requires it for correctness.

## Minimum tests

- Service returns cached data without querying PostgreSQL.
- Cache miss queries PostgreSQL and repopulates Redis.
- Update and delete change PostgreSQL before invalidating Redis.
- Missing user becomes HTTP `404`.
- Invalid payload becomes HTTP `422`.
- PostgreSQL failure produces the chosen availability response.
- Optional Redis failure falls back to PostgreSQL.
- Lifespan closes both connection objects.

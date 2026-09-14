---
name: fastapi-pragmatic-layered
description: Create or refactor FastAPI services using a pragmatic layered architecture with routers, schemas, services, consistent infrastructure adapters, and tests. Use when the user wants technology-independent services without the ceremony of full Clean Architecture, Hexagonal Architecture, or DDD.
---

# FastAPI Pragmatic Layered Architecture

Build the smallest maintainable FastAPI service that satisfies the request. Keep the architecture simple and add integrations only when the API actually needs them.

## Layer boundaries

Use these responsibilities:

- `main.py`: application construction, router registration, lifespan, and composition of dependencies.
- `routers/`: HTTP transport only—parameters, authentication dependencies, status codes, and translation between HTTP and the service call.
- `schemas/`: Pydantic request, response, and integration payload contracts.
- `service/`: application operations, business decisions, and workflow coordination.
- `infra/`: database, queues, cache, filesystem, and external API adapters.
- `tests/`: observable behavior at service and HTTP boundaries.

Keep the normal dependency flow:

```text
router -> service -> injected infrastructure
```

## Integration pattern

Keep every external integration consistent:

```text
infra/<integration>/connection.py
infra/<integration>/<resource>_repository.py  # persistence or cache
infra/<integration>/<provider>_client.py       # remote HTTP API
```

- `connection.py` owns client construction, configuration, health checks, pooling, and shutdown. It must not contain application workflows.
- A repository, cache adapter, producer, or API client owns technology-specific operations.
- A service receives that behavior through constructor injection. It must not create connections or import a concrete Redis, PostgreSQL, broker, or HTTP client.
- Put connection construction and concrete wiring in `main.py` or `dependencies.py`.
- Use a small `Protocol` at the service boundary when it materially keeps the service independent and makes fakes straightforward. Do not create a hierarchy of interfaces for its own sake.

Apply the same concept to every technology. For example, Redis uses `connection.py` plus a cache adapter; PostgreSQL uses `connection.py` plus a repository; an external API uses `connection.py` plus a provider client.

Do not let infrastructure call routers or place business decisions in route handlers. Avoid circular imports. Construct concrete dependencies in `main.py`, a small dependency module, or FastAPI dependencies—choose the simplest option that fits the service.

## Default shape

For a new API, begin with this shape and omit unused directories:

```text
src/
|-- main.py
|-- routers/
|   `-- <resource>.py
|-- schemas/
|   `-- <resource>.py
|-- service/
|   `-- <resource>_service.py
`-- infra/
    `-- <required integration>/
tests/
```

Follow an established repository layout and naming convention when one already exists instead of forcing this exact tree.

## Implementation workflow

1. Inspect repository instructions, dependency files, existing modules, tests, and uncommitted changes before editing.
2. Identify the HTTP contract, application operation, and genuinely required external integrations.
3. Define Pydantic schemas and explicit response models.
4. Implement the service independently of FastAPI request objects. Inject external collaborators through its constructor or function parameters.
5. Implement infrastructure behind a small behavior-focused API. Introduce `Protocol` or `ABC` interfaces only when substitution, multiple implementations, or an important test boundary justifies them.
6. Keep route handlers thin: validate, call the service, translate expected failures to HTTP responses, and return the declared schema.
7. Wire resources into application lifespan when they require startup or shutdown. Keep liveness endpoints cheap and independent of optional infrastructure.
8. Add focused tests for health, success, validation failure, and expected infrastructure failure. Run the repository's formatter, linter, tests, import check, and relevant container configuration validation.

When PostgreSQL is the source of truth and Redis is a cache, read [Redis and PostgreSQL example](references/redis-postgres-example.md). Use it as a pattern, not as mandatory boilerplate.

## Pragmatic constraints

- Do not add domain entities, use-case classes, factories, CQRS, or event abstractions by default. Add only the small repository or client boundary required to isolate an external integration.
- Do not add PostgreSQL, Redis, RabbitMQ, tracing, authentication, or Docker unless requested or already required by the surrounding project.
- Preserve existing behavior and public contracts during refactors unless the user requests a breaking change.
- Keep secrets out of source code; use settings or environment variables and provide safe local defaults only when appropriate.
- Prefer async libraries in `async def` paths. Run unavoidable blocking I/O in a synchronous route or an appropriate thread boundary.
- For queued commands, return `202 Accepted` only after the broker confirms acceptance; return a deliberate availability error when publishing fails.
- Do not claim end-to-end success when an external dependency was mocked or unavailable. Report unit, integration, and live checks separately.

## Completion report

State what was created or changed, which checks passed, and which external integrations were not exercised. Mention preserved user changes and any remaining operational requirement without proposing unrelated expansion.

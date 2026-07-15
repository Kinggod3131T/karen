#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_ROOT="$(pwd)"

if [[ ! -d "$PROJECT_ROOT/services/core" ]]; then
    echo "Run this script from the Karen repository root."
    exit 1
fi

echo "Creating Karen platform structure..."

mkdir -p \
    services/core/app/clients \
    services/core/app/routes \
    services/core/app/tools \
    services/core/app/security \
    services/router \
    agents/planner \
    agents/coder \
    agents/reviewer \
    agents/devops \
    agents/documentation \
    prompts/system \
    memory \
    configs/litellm \
    infrastructure/docker \
    infrastructure/kubernetes \
    workflows/n8n \
    scripts \
    tests

touch \
    services/__init__.py \
    services/core/__init__.py \
    services/core/app/__init__.py \
    services/core/app/clients/__init__.py \
    services/core/app/routes/__init__.py \
    services/core/app/tools/__init__.py \
    services/core/app/security/__init__.py

cat > requirements.txt <<'EOF'
fastapi
uvicorn[standard]
pydantic
pydantic-settings
httpx
psutil
python-dotenv
redis
sqlalchemy
asyncpg
qdrant-client
EOF

cat > .env.example <<'EOF'
APP_NAME=Karen Core
APP_VERSION=0.3.0

KAREN_WORKSPACE=/home/kabeer/Workspace
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5-coder:3b

POSTGRES_USER=karen
POSTGRES_PASSWORD=change-this-password
POSTGRES_DB=karen
POSTGRES_PORT=5432

REDIS_PORT=6379
QDRANT_PORT=6333
OPEN_WEBUI_PORT=3000
N8N_PORT=5678

OPENROUTER_API_KEY=
EOF

if [[ ! -f .env ]]; then
    cp .env.example .env
fi

cat > services/core/app/settings.py <<'EOF'
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Karen Core"
    app_version: str = "0.3.0"

    karen_workspace: Path = Path.home() / "Workspace"

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5-coder:3b"

    postgres_user: str = "karen"
    postgres_password: str = "change-this-password"
    postgres_db: str = "karen"
    postgres_port: int = 5432

    redis_port: int = 6379
    qdrant_port: int = 6333

    openrouter_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
EOF

cat > services/core/app/schemas.py <<'EOF'
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=30_000)
    model: str | None = None


class ChatResponse(BaseModel):
    model: str
    response: str
    done: bool


class FilePathRequest(BaseModel):
    path: str = Field(min_length=1)


class FileWriteRequest(BaseModel):
    path: str = Field(min_length=1)
    content: str
    confirm: bool = False
EOF

cat > services/core/app/security/workspace.py <<'EOF'
from pathlib import Path

from fastapi import HTTPException

from services.core.app.settings import settings


def resolve_workspace_path(user_path: str) -> Path:
    workspace = settings.karen_workspace.expanduser().resolve()
    requested = Path(user_path).expanduser()

    if not requested.is_absolute():
        requested = workspace / requested

    resolved = requested.resolve(strict=False)

    try:
        resolved.relative_to(workspace)
    except ValueError as exc:
        raise HTTPException(
            status_code=403,
            detail="Access outside the configured workspace is forbidden.",
        ) from exc

    return resolved
EOF

cat > services/core/app/clients/ollama.py <<'EOF'
from typing import Any

import httpx
from fastapi import HTTPException

from services.core.app.settings import settings


async def list_models() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.ollama_base_url}/api/tags"
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama is unavailable: {exc}",
        ) from exc


async def generate(prompt: str, model: str | None = None) -> dict[str, Any]:
    selected_model = model or settings.ollama_model

    payload = {
        "model": selected_model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="The local model exceeded the response timeout.",
        ) from exc

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Local model request failed: {exc}",
        ) from exc
EOF

cat > services/core/app/tools/filesystem.py <<'EOF'
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from services.core.app.security.workspace import resolve_workspace_path


def list_directory(path: str) -> dict[str, Any]:
    resolved = resolve_workspace_path(path)

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Path does not exist.")

    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory.")

    entries = []

    for item in sorted(resolved.iterdir(), key=lambda entry: entry.name.lower()):
        entries.append(
            {
                "name": item.name,
                "path": str(item),
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
            }
        )

    return {
        "path": str(resolved),
        "entries": entries,
    }


def read_text_file(path: str) -> dict[str, str]:
    resolved = resolve_workspace_path(path)

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="File does not exist.")

    if not resolved.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file.")

    if resolved.stat().st_size > 2_000_000:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 2 MB reading limit.",
        )

    try:
        content = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=415,
            detail="Only UTF-8 text files are supported.",
        ) from exc

    return {
        "path": str(resolved),
        "content": content,
    }


def write_text_file(path: str, content: str, confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise HTTPException(
            status_code=409,
            detail="Writing requires confirm=true.",
        )

    resolved = resolve_workspace_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)

    previous_content: str | None = None

    if resolved.exists():
        if not resolved.is_file():
            raise HTTPException(
                status_code=400,
                detail="Target path is not a regular file.",
            )

        try:
            previous_content = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            previous_content = None

        backup_path = resolved.with_suffix(resolved.suffix + ".karen-backup")
        backup_path.write_bytes(resolved.read_bytes())

    resolved.write_text(content, encoding="utf-8")

    return {
        "path": str(resolved),
        "written": True,
        "created": previous_content is None,
        "backup_created": previous_content is not None,
    }
EOF

cat > services/core/app/routes/system.py <<'EOF'
from typing import Any

import psutil
from fastapi import APIRouter

from services.core.app.settings import settings


router = APIRouter(tags=["System"])


@router.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Karen",
        "version": settings.app_version,
        "status": "online",
    }


@router.get("/health")
def health() -> dict[str, Any]:
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")

    return {
        "status": "healthy",
        "memory": {
            "total_gib": round(memory.total / 1024**3, 2),
            "available_gib": round(memory.available / 1024**3, 2),
            "used_percent": memory.percent,
        },
        "swap": {
            "total_gib": round(swap.total / 1024**3, 2),
            "used_gib": round(swap.used / 1024**3, 2),
            "used_percent": swap.percent,
        },
        "disk": {
            "total_gib": round(disk.total / 1024**3, 2),
            "free_gib": round(disk.free / 1024**3, 2),
            "used_percent": disk.percent,
        },
    }
EOF

cat > services/core/app/routes/ai.py <<'EOF'
from typing import Any

from fastapi import APIRouter

from services.core.app.clients.ollama import generate, list_models
from services.core.app.schemas import ChatRequest, ChatResponse


router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/models")
async def models() -> dict[str, Any]:
    return await list_models()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    result = await generate(
        prompt=request.prompt,
        model=request.model,
    )

    return ChatResponse(
        model=result.get("model", request.model or "unknown"),
        response=result.get("response", ""),
        done=result.get("done", False),
    )
EOF

cat > services/core/app/routes/files.py <<'EOF'
from typing import Any

from fastapi import APIRouter

from services.core.app.schemas import FilePathRequest, FileWriteRequest
from services.core.app.tools.filesystem import (
    list_directory,
    read_text_file,
    write_text_file,
)


router = APIRouter(prefix="/tools/files", tags=["File tools"])


@router.post("/list")
def list_path(request: FilePathRequest) -> dict[str, Any]:
    return list_directory(request.path)


@router.post("/read")
def read_file(request: FilePathRequest) -> dict[str, str]:
    return read_text_file(request.path)


@router.post("/write")
def write_file(request: FileWriteRequest) -> dict[str, Any]:
    return write_text_file(
        path=request.path,
        content=request.content,
        confirm=request.confirm,
    )
EOF

cat > services/core/app/main.py <<'EOF'
from fastapi import FastAPI

from services.core.app.routes import ai, files, system
from services.core.app.settings import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Local-first AI workstation orchestration service with "
        "controlled workspace tools."
    ),
)

app.include_router(system.router)
app.include_router(ai.router)
app.include_router(files.router)
EOF

cat > services/core/Dockerfile <<'EOF'
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services /app/services

CMD [
  "uvicorn",
  "services.core.app.main:app",
  "--host",
  "0.0.0.0",
  "--port",
  "8080"
]
EOF

cat > configs/litellm/config.yaml <<'EOF'
model_list:
  - model_name: local-coder
    litellm_params:
      model: ollama/qwen2.5-coder:3b
      api_base: http://host.docker.internal:11434

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
EOF

cat > compose.yaml <<'EOF'
services:
  postgres:
    image: postgres:17-alpine
    container_name: karen-postgres
    profiles: ["data", "full"]
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - karen_postgres:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:${POSTGRES_PORT}:5432"
    mem_limit: 512m

  redis:
    image: redis:8-alpine
    container_name: karen-redis
    profiles: ["data", "full"]
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - karen_redis:/data
    ports:
      - "127.0.0.1:${REDIS_PORT}:6379"
    mem_limit: 256m

  qdrant:
    image: qdrant/qdrant:latest
    container_name: karen-qdrant
    profiles: ["memory", "full"]
    restart: unless-stopped
    volumes:
      - karen_qdrant:/qdrant/storage
    ports:
      - "127.0.0.1:${QDRANT_PORT}:6333"
    mem_limit: 512m

  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: karen-open-webui
    profiles: ["ui", "full"]
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      OLLAMA_BASE_URL: http://host.docker.internal:11434
    volumes:
      - karen_open_webui:/app/backend/data
    ports:
      - "127.0.0.1:${OPEN_WEBUI_PORT}:8080"
    mem_limit: 1g

  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    container_name: karen-litellm
    profiles: ["router", "full"]
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      LITELLM_MASTER_KEY: ${LITELLM_MASTER_KEY:-change-me}
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY:-}
    volumes:
      - ./configs/litellm/config.yaml:/app/config.yaml:ro
    command: ["--config", "/app/config.yaml", "--port", "4000"]
    ports:
      - "127.0.0.1:4000:4000"
    mem_limit: 512m

  n8n:
    image: docker.n8n.io/n8nio/n8n:latest
    container_name: karen-n8n
    profiles: ["automation", "full"]
    restart: unless-stopped
    environment:
      N8N_HOST: 127.0.0.1
      N8N_PORT: 5678
      N8N_PROTOCOL: http
      GENERIC_TIMEZONE: Asia/Kolkata
    volumes:
      - karen_n8n:/home/node/.n8n
    ports:
      - "127.0.0.1:${N8N_PORT}:5678"
    mem_limit: 768m

volumes:
  karen_postgres:
  karen_redis:
  karen_qdrant:
  karen_open_webui:
  karen_n8n:
EOF

cat > scripts/run-core.sh <<'EOF'
#!/usr/bin/env bash

set -Eeuo pipefail

cd "$(dirname "$0")/.."

source .venv/bin/activate

exec uvicorn \
    services.core.app.main:app \
    --reload \
    --host 127.0.0.1 \
    --port 8080
EOF

cat > scripts/status.sh <<'EOF'
#!/usr/bin/env bash

echo "=== Karen services ==="
systemctl is-active ollama || true
docker compose ps || true

echo
echo "=== Memory ==="
free -h

echo
echo "=== Swap ==="
swapon --show
EOF

chmod +x scripts/run-core.sh scripts/status.sh bootstrap-karen.sh

cat > README.md <<'EOF'
# Karen

Karen is a local-first AI workstation platform.

## Current capabilities

- FastAPI orchestration service
- Ollama integration
- Local coding model
- Safe workspace-scoped file listing
- Safe text file reading
- Confirmed file writing with automatic backups
- Optional PostgreSQL, Redis, Qdrant, LiteLLM, Open WebUI and n8n services

## Start Karen Core

```bash
source .venv/bin/activate
./scripts/run-core.sh

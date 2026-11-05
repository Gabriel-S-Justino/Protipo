"""Aplicação FastAPI da Fire Intelligence Platform.

Rodar localmente (sem Docker):
    uvicorn backend.app.main:app --reload --port 8000

Documentação OpenAPI: http://localhost:8000/api/docs
Na Vercel: rewrites "/api/(.*)" → api/index.py (ver docs/VERCEL.md).
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api import dashboard, detections, health, series
from backend.app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Fire Intelligence Platform API",
    version="0.1.0",
    description=(
        "API de leitura da série histórica unificada de focos de calor (MODIS→VIIRS) "
        "e do calendário probabilístico. A API APENAS lê resultados pré-calculados "
        "pelo pipeline científico; nenhum processamento pesado em requisição."
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS restrito: em produção, CORS_ORIGINS deve apontar o domínio do SPA ("*" proibido).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(detections.router, prefix="/api")
app.include_router(series.router, prefix="/api")


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    # Erros padronizados; sem vazamento de detalhes internos em produção.
    detail = str(exc) if settings.app_env != "production" else "Erro interno."
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": detail})


@app.get("/api")
def root() -> dict:
    return {
        "name": settings.app_name,
        "docs": "/api/docs",
        "note": "A API lê resultados pré-calculados pelo pipeline; nenhum processamento científico em requisição.",
    }

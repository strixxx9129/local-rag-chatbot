# backend/src/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.v1 import auth as auth_router
from src.api.v1 import documents as documents_router   # ← ADD THIS
from src.api.v1 import stream as stream_router 
from src.api.v1 import rag as rag_router 
from src.core.config import settings
from src.core.exceptions import AppError
from src.core.logging import logger

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    debug=settings.app_debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        "app.error",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


app.include_router(auth_router.router, prefix=settings.api_prefix)
app.include_router(documents_router.router, prefix=settings.api_prefix)  # ← ADD THIS
app.include_router(rag_router.router, prefix=settings.api_prefix)
app.include_router(stream_router.router, prefix=settings.api_prefix)


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}
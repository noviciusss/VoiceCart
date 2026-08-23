from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from db import get_pool, close_pool
from routers import command, items, suggestions


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB pool + run migrations
    await get_pool()
    yield
    # Shutdown: close pool
    await close_pool()


app = FastAPI(
    title="Voice Command Shopping Assistant",
    description="Voice-first grocery list assistant powered by Groq LLM",
    version="1.0.0",
    lifespan=lifespan,
)

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

# Global middleware to ensure CORS headers on ALL responses (including errors and preflight)
@app.middleware("http")
async def universal_cors_middleware(request, call_next):
    if request.method == "OPTIONS":
        response = Response(status_code=200)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "86400"
        return response

    try:
        response = await call_next(request)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        response = JSONResponse(
            status_code=500,
            content={"detail": f"Internal Server Error: {str(exc)}"}
        )

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(command.router)
app.include_router(items.router)
app.include_router(suggestions.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

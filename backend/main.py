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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://voice-cart-chi.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ],
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(command.router)
app.include_router(items.router)
app.include_router(suggestions.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

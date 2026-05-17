from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import engine, Base
from app.api.v1.endpoints import users, rewards, plants, waste_classification


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ EcoExchange API ready — http://localhost:8000/docs")
    yield
    await engine.dispose()


app = FastAPI(
    title="Namma EcoExchange API",
    description="Organic waste → Green Points → Bio-Gas cylinders",
    version="1.0.0",
    # lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router,      prefix="/api/v1")
app.include_router(rewards.router,    prefix="/api/v1")
app.include_router(plants.router,     prefix="/api/v1")
app.include_router(waste_classification.router, prefix="/api/v1")  # includZe waste classification routes at the top level


@app.get("/health")
async def health():
    return {"status": "ok"}

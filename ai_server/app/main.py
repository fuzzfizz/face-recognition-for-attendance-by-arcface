from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db
from app.routers import registration, training, verification, logs
from app.routers.v1 import users as v1_users

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Face Recognition AI Server",
    description="ArcFace + Supabase hybrid attendance system",
    version="5.0.0",
    lifespan=lifespan,
)

@app.get("/", tags=["health"])
def health():
    from app.database import using_supabase
    return {"status": "ok", "mode": "supabase" if using_supabase() else "sqlite"}

app.include_router(registration.router)
app.include_router(training.router)
app.include_router(verification.router)
app.include_router(logs.router)
app.include_router(v1_users.router, prefix="/v1", tags=["legacy-v1"])

if __name__ == "__main__":
    import uvicorn
    from app.config import HOST, PORT
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
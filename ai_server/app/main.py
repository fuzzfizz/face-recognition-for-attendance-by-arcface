import asyncio
import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import TRAINING_SCHEDULE_TIMES
from app.database import init_db
from app.routers import registration, training, verification, logs
from app.routers.v1 import users as v1_users

async def run_training_scheduler():
    times = [t.strip() for t in TRAINING_SCHEDULE_TIMES.split(",") if t.strip()]
    if not times:
        print("[Scheduler] No training schedule configured.")
        return

    print(f"[Scheduler] Active. Schedule slots: {times}")
    while True:
        now = datetime.datetime.now()
        current_time_str = now.strftime("%H:%M")
        if current_time_str in times:
            print(f"[Scheduler] Running scheduled queue training at {current_time_str}...")
            try:
                from app.services.training_service import process_pending_queue
                process_pending_queue()
            except Exception as e:
                print(f"[Scheduler] Scheduled training failed: {e}")
            await asyncio.sleep(61)  # Skip remainder of the minute
        else:
            await asyncio.sleep(20)  # Check every 20 seconds

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler_task = asyncio.create_task(run_training_scheduler())
    yield
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="Face Recognition AI Server",
    description="ArcFace attendance system",
    version="5.0.0",
    lifespan=lifespan,
)

@app.get("/", tags=["health"])
def health():
    from app.config import MYSQL_URL
    actual_mode = "mysql" if (MYSQL_URL and not MYSQL_URL.startswith("sqlite")) else "sqlite"
    return {"status": "ok", "mode": actual_mode}

app.include_router(registration.router)
app.include_router(training.router)
app.include_router(verification.router)
app.include_router(logs.router)
app.include_router(v1_users.router, prefix="/v1", tags=["legacy-v1"])

if __name__ == "__main__":
    import uvicorn
    from app.config import HOST, PORT
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
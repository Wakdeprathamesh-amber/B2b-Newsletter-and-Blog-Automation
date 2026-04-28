"""Amber Content Engine -- Main entry point.

Runs the FastAPI server with:
- API endpoints for cycle management and human gates
- APScheduler for automated bi-monthly cycle triggers
- Database initialization
"""

import uvicorn
from fastapi import FastAPI

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.api.routes import router
from src.api.ui_routes import router as ui_router
from src.models.database import init_db
from src.settings import settings

app = FastAPI(
    title="Amber Content Engine",
    description="Automated B2B content pipeline for amber",
    version="0.2.0",
)

app.include_router(router)
app.include_router(ui_router)


@app.get("/")
async def serve_dashboard():
    """Serve the control panel UI."""
    return FileResponse("static/index.html")


@app.on_event("startup")
async def startup():
    """Initialize database and optionally start scheduler."""
    init_db()

    if settings.dev_mode:
        print("--- DEV MODE: scheduler disabled, using sample data ---")
        return

    # Production: set up APScheduler for automated cycle triggers (optional)
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = AsyncIOScheduler(timezone=settings.timezone)
        scheduler.add_job(
            _trigger_scheduled_cycle,
            CronTrigger.from_crontab(settings.cycle_cron),
            id="cycle_trigger",
            replace_existing=True,
        )
        scheduler.start()
        app.state.scheduler = scheduler
    except ImportError:
        print("APScheduler not installed — automatic scheduling disabled. Use the web UI instead.")


async def _trigger_scheduled_cycle():
    """Automatically trigger a new cycle on schedule."""
    from datetime import datetime, timezone as tz
    from src.api.routes import trigger_cycle, TriggerCycleRequest

    cycle_id = f"{datetime.now(tz.utc).strftime('%Y-W%V')}"
    await trigger_cycle(TriggerCycleRequest(cycle_id=cycle_id))


@app.on_event("shutdown")
async def shutdown():
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler:
        scheduler.shutdown()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "dev_mode": settings.dev_mode,
        "llm_available": settings.is_llm_available,
    }


def main():
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


if __name__ == "__main__":
    main()

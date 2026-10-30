import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.db import init_db
from app.routes import auth, briefing, command, suggest, tasks, weekplan


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="task-flow API", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(suggest.router)
app.include_router(briefing.router)
app.include_router(weekplan.router)
app.include_router(command.router)


@app.exception_handler(sqlite3.Error)
def storage_error(request: Request, exc: sqlite3.Error) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "저장소 오류"})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

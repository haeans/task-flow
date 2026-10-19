from fastapi import FastAPI

app = FastAPI(title="task-flow API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

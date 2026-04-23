from fastapi import FastAPI

from app.core.exceptions import register_exception_handlers

app = FastAPI(
    title="Portfolio Backend",
    version="0.1.0",
    docs_url="/docs" if True else None,
    redoc_url=None,
)

register_exception_handlers(app)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse

from routers import blobs, certificates, templates

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Warming up templates...")
    templates.warm_up_templates()
    logger.info("Templates warmed up")
    yield
    logger.info("Server shutting down")


app = FastAPI(
    title="Oicana example",
    description="Python FastAPI example with Oicana",
    version="1.0",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(templates.router, prefix="/templates", tags=["template"])
app.include_router(certificates.router, prefix="/certificates", tags=["certificates"])
app.include_router(blobs.router, prefix="/blobs", tags=["blob"])


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    return 'Visit the swagger documentation at <a href="/docs">/docs</a>'


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=3003)

import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.routers import fii
from communication.exceptions import NoDataForExportError, ScrapingError
from infrastructure.scheduler_service import SchedulerService

logging.basicConfig(level=logging.INFO)

scheduler_service = SchedulerService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_service.start()
    yield
    scheduler_service.shutdown()

app = FastAPI(title="Investe AI API", lifespan=lifespan)

app.include_router(fii.router)

@app.exception_handler(ScrapingError)
def handle_scraping_error(request: Request, exc: ScrapingError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})

@app.exception_handler(NoDataForExportError)
def handle_no_data_error(request: Request, exc: NoDataForExportError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
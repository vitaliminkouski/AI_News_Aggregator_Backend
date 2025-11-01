import uvicorn
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from app.api.v1.testroutes import router as test_router
from app.api.v1.auth_routes import router as auth_router
from app.core.logging_config import setup_logging, get_logger

setup_logging()
logger=get_logger(__name__)

logger.info("News Bot API starting up...")

app=FastAPI()
app.include_router(test_router)
app.include_router(auth_router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return {"message": "Hello world"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
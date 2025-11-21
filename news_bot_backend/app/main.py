import uvicorn
from fastapi import FastAPI

from app.api.v1.articles import router as articles_router
from app.api.v1.sources import router as sources_router
from app.api.v1.testroutes import router as test_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)
api_prefix = settings.API_PREFIX or ""
app.include_router(test_router, prefix=api_prefix)
app.include_router(sources_router, prefix=api_prefix)
app.include_router(articles_router, prefix=api_prefix)


@app.get("/")
def index():
    return {"message": "Hello world"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

import uvicorn
from fastapi import FastAPI, APIRouter
from fastapi.openapi.utils import get_openapi
from starlette.staticfiles import StaticFiles

from app.api.v1.register_route import router as register_router
from app.api.v1.auth_routes import router as auth_router
from app.api.v1.news_routes import router as news_router
from app.api.v1.articles import router as articles_router
from app.api.v1.source_router import router as source_router
from app.api.v1.profile_routes import router as profile_router
from app.api.v1.topic_routes import router as topic_router
from app.api.v1.user_source_router import router as user_source_router
from app.api.v1.email_routes import router as email_router
from app.api.v1.admin_user_router import router as admin_user_router

from app.core.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

logger.info("News Bot API starting up...")

app = FastAPI()

api_v1=APIRouter(prefix="/api/v1")

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="News Bot API",
        version="1.0.0",
        description="API for News Bot application",
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/auth/login/",
                    "scopes": {}
                }
            }
        },
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your access token (without 'Bearer' prefix)"
        }
    }

    # Apply bearerAuth to all paths that require authentication
    # This makes Swagger UI show the lock icon and allow token entry
    for path, path_item in openapi_schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method in ["get", "post", "put", "patch", "delete"]:
                # Check if this endpoint uses get_current_user (has security requirements)
                # We'll add bearerAuth as an option for all endpoints
                # FastAPI will automatically add OAuth2PasswordBearer, we add bearerAuth too
                if "security" not in operation:
                    # If no security is defined, check if it should have it
                    # For now, we'll let FastAPI handle it automatically
                    pass
                else:
                    # Add bearerAuth as an alternative
                    if isinstance(operation.get("security"), list):
                        operation["security"].append({"bearerAuth": []})
                    else:
                        operation["security"] = [
                            operation.get("security", {}),
                            {"bearerAuth": []}
                        ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

api_v1.include_router(register_router)
api_v1.include_router(auth_router)
api_v1.include_router(news_router)
api_v1.include_router(articles_router)
api_v1.include_router(source_router)
api_v1.include_router(profile_router)
api_v1.include_router(topic_router)
api_v1.include_router(user_source_router)
api_v1.include_router(email_router)
api_v1.include_router(admin_user_router)

app.include_router(api_v1)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return {"message": "Hello world"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

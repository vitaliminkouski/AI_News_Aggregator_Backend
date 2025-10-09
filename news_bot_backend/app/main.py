import uvicorn
from fastapi import FastAPI
from app.api.v1.testroutes import router as test_router
app=FastAPI()
app.include_router(test_router)


@app.get("/")
def index():
    return {"message": "Hello world"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
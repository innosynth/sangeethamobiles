import logging
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from User.api import router as user_router

load_dotenv()
app = FastAPI(
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/documentation",
    redoc_url="/api/v1/redoc",
)


app.include_router(user_router, prefix="/api/v1", tags=["User"])
# Simple route for basic testing and healthcheck
@app.get("/")
def hello_world():
    return "Hello, World!"

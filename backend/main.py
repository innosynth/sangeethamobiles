import logging
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from backend.Business.api import router as business_router
from backend.Store.api import router as store_router
from backend.Login.api import router as login_router
from backend.User.api import router as user_router

load_dotenv()
app = FastAPI(
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/documentation",
    redoc_url="/api/v1/redoc",
)


app.include_router(business_router)
app.include_router(store_router)
app.include_router(login_router)
# app.include_router(user_router)
# Simple route for basic testing and healthcheck
@app.get("/")
def hello_world():
    return "Hello, World!"

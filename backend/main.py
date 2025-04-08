from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from backend.Business.api import router as business_router
from backend.Store.api import router as store_router
from backend.Login.api import router as login_router
from backend.User.api import router as user_router
from backend.AudioProcessing.api import router as audio_router
from backend.Feedback.api import router as feedback_router
from backend.Dashboard.api import router as dashboard_router
from backend.Area.api import router as area_router
from backend.Transcription.api import router as transcription_router


app = FastAPI(
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/documentation",
    redoc_url="/api/v1/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(business_router)
app.include_router(store_router)
app.include_router(login_router)
app.include_router(user_router)
app.include_router(audio_router)
app.include_router(feedback_router)
app.include_router(dashboard_router)
app.include_router(area_router)
app.include_router(transcription_router)


# Simple route for basic testing and healthcheck
@app.get("/")
def hello_world():
    return "Hello, World!"

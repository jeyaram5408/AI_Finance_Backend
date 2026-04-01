import os
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from app.dependencies.database_init import init_db
from app.core.exception_handlers import register_exception_handlers
from app.routers.admin_media_router import router as admin_media_router


import app.models

from app.routers import (
    dashboard_routes,
    profile_details,
    transaction_routes,
    category_routes,
    report_routes,
    forecast_router,
    auth_router,
    user_api,
    financial_health_router,
    ai_suggestion,
)
from app.routers.goal_router import router as goal_router
from app.routers.settings_router import router as settings_router
from app.routers.profile_picture import router as profile_picture_router
from app.routers.feature_routes import router as feature_router
from app.routers.admin_router import router as admin_router
from app.routers.admin_update import router as admin_update_router

app = FastAPI(title="AI Finance Advisor API", version="1.0.0")
load_dotenv() 
register_exception_handlers(app)
frontend_url = os.getenv("FRONTEND_URL")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url] if frontend_url else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# os.makedirs("uploads/profile", exist_ok=True)
# app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

os.makedirs("uploads/profile", exist_ok=True)
os.makedirs("uploads/admin_media", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")



@app.on_event("startup")
async def startup():
    await init_db()


app.include_router(auth_router.router)
app.include_router(transaction_routes.router)
app.include_router(category_routes.router)
app.include_router(report_routes.router)
app.include_router(forecast_router.router)
app.include_router(dashboard_routes.router)
app.include_router(user_api.router)
app.include_router(profile_details.router)
app.include_router(profile_picture_router)
app.include_router(financial_health_router.router)
app.include_router(ai_suggestion.router)
app.include_router(goal_router)
app.include_router(settings_router)
app.include_router(feature_router)

app.include_router(admin_router)
app.include_router(admin_update_router)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

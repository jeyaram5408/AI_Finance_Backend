

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn ,os
from app.core.config import FRONTEND_URL

from app.core.exception_handlers import register_exception_handlers
from app.dependencies.database_init import init_db


from app.routers import (
    dashboard_routes,
    profile_details,
    transaction_routes,
    report_routes,
    forecast_router,
    auth_router,
    user_api,
    financial_health_router,
)

from app.routers.category_routes import router as category_router
from app.routers.goal_router import router as goal_router
from app.routers.settings_router import router as settings_router
from app.routers.profile_picture import router as profile_picture_router
from app.routers.feature_routes import router as feature_router
from app.routers.admin_router import router as admin_router
from app.routers.admin_update import router as admin_update_router
from app.routers.admin_media_router import router as admin_media_router
from app.routers.ai_suggestion import router as ai_suggestion_router
from app.routers.api_protection import router as api_protection_router


# ENV = os.getenv("ENV", "local")
# load_dotenv(".env" if ENV == "production" else ".env.local")

app = FastAPI(title="AI Finance Advisor API", redirect_slashes=True)




frontend_url = (FRONTEND_URL or "").strip()

origins = [
    "http://localhost:5173",
    frontend_url
]

print("🔥 FRONTEND URL:", frontend_url)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin for origin in origins if origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.options("/{full_path:path}")
async def preflight_handler(full_path: str):
    return {"message": "OK"}

register_exception_handlers(app)

os.makedirs("uploads/profile", exist_ok=True)
os.makedirs("uploads/admin_media", exist_ok=True)

# profile images only public
app.mount("/uploads/profile", StaticFiles(directory="uploads/profile"), name="profile-uploads")


@app.get("/")
def root():
    return {"message": "API is running"}


@app.on_event("startup")
async def startup():
    await init_db()


app.include_router(auth_router.router)
app.include_router(transaction_routes.router)
app.include_router(category_router)
app.include_router(report_routes.router)
app.include_router(forecast_router.router)
app.include_router(dashboard_routes.router)
app.include_router(user_api.router)
app.include_router(profile_details.router)
app.include_router(profile_picture_router)
app.include_router(financial_health_router.router)
app.include_router(ai_suggestion_router)
app.include_router(goal_router)
app.include_router(settings_router)
app.include_router(feature_router)
app.include_router(admin_router)
app.include_router(admin_update_router)
app.include_router(admin_media_router)
app.include_router(api_protection_router)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

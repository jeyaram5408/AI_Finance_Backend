from app.dependencies.auth_dependency import get_current_user
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/protection", tags=["Protection"])

@router.get("/test-protected")
async def protected_route(current_user = Depends(get_current_user)):
    
    return {
    "message": "You are authorized",
    "user": {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name
    }
}
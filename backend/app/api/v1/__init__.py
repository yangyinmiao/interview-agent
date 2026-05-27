from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.resumes import router as resumes_router
from app.api.v1.jds import router as jds_router
from app.api.v1.question_banks import router as qb_router
from app.api.v1.interviews import router as interviews_router
from app.api.v1.admin import router as admin_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(resumes_router)
api_router.include_router(jds_router)
api_router.include_router(qb_router)
api_router.include_router(interviews_router)
api_router.include_router(admin_router)

from fastapi import APIRouter

import config
from database import check_db_health

router = APIRouter()


@router.get("/health")
@router.get("/healthz")  # k8s-style alias; both resolve to the same check
async def health():
    db_ok = await check_db_health()
    return {
        "status": "healthy" if db_ok else "degraded",
        "service": config.APP_NAME,
        "version": config.APP_VERSION,
        "db": db_ok,
    }

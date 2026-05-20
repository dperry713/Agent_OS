from fastapi import APIRouter
import time

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok", "timestamp": time.time()}
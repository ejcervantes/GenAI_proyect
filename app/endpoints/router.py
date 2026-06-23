from fastapi import APIRouter
from app.endpoints import health, auth, rag, chat, checklists, change_alerts, documents

router = APIRouter()

router.include_router(health.router, tags=["Health"])
router.include_router(auth.router, prefix="/auth", tags=["Auth"])
router.include_router(rag.router, prefix="/rag", tags=["RAG"])
router.include_router(chat.router, prefix="/chat", tags=["Chat"])
router.include_router(checklists.router, prefix="/checklists", tags=["Checklists"])
router.include_router(
    checklists.visa_cases_router, prefix="/visa-cases", tags=["Visa Cases"]
)
router.include_router(
    change_alerts.router, prefix="/change-alerts", tags=["Change Alerts"]
)
router.include_router(documents.router, prefix="/documents", tags=["Documents"])

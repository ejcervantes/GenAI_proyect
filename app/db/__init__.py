from app.db.base import Base

# Import all models here so Alembic autogenerate can detect them
from app.models.user import User  # noqa: F401
from app.models.visa_case import VisaCase  # noqa: F401
from app.models.checklist import Checklist, ChecklistItem  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.change_alert import ChangeAlert  # noqa: F401
from app.models.rag_interaction import RAGInteraction  # noqa: F401

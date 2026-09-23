from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database.db import get_db, store_ticket
from app.schemas.tickets import TicketCreate, TicketResponse
from app.services.classifier import InvalidCategoryError, classify_ticket
from app.services.ollama_client import OllamaError

router = APIRouter()


@router.post("/tickets", response_model=TicketResponse, status_code=201)
def submit_ticket(payload: TicketCreate, request: Request, db: Session = Depends(get_db)):
    try:
        category = classify_ticket(payload.narrative)
    except (InvalidCategoryError, OllamaError) as exc:
        request.state.error = type(exc).__name__
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    request.state.predicted_category = category
    return store_ticket(db, payload.narrative, category, settings.ollama_model)

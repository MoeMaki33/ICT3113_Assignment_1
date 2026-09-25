from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.db import get_db, search_tickets
from app.schemas.tickets import TicketRead

router = APIRouter()


@router.get("/search", response_model=list[TicketRead])
def search(q: str = Query(min_length=1), db: Session = Depends(get_db)):
    q = q.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Search query must not be blank")
    return search_tickets(db, q)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.db import category_counts, get_db

router = APIRouter()


@router.get("/stats", response_model=dict[str, int])
def stats(db: Session = Depends(get_db)):
    return category_counts(db)

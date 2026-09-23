from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.categories import CATEGORIES
from app.config import settings
from app.database.models import Base, Ticket


def build_engine(database_url: str):
    url = make_url(database_url)
    connect_args = {}
    if url.get_backend_name() == "sqlite":
        connect_args = {"check_same_thread": False}
        if url.database and url.database != ":memory:":
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(database_url, connect_args=connect_args)


engine = build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    # Create tables only; never seed or erase tickets on startup.
    Base.metadata.create_all(engine)


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def store_ticket(session: Session, narrative: str, category: str, model: str) -> Ticket:
    ticket = Ticket(narrative=narrative, category=category, model=model)
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return ticket


def search_tickets(session: Session, query: str) -> list[Ticket]:
    statement = select(Ticket).where(
        Ticket.narrative.contains(query, autoescape=True)
    ).order_by(Ticket.id)
    return list(session.scalars(statement))


def category_counts(session: Session) -> dict[str, int]:
    counts = dict.fromkeys(CATEGORIES, 0)
    counts.update(session.execute(
        select(Ticket.category, func.count(Ticket.id)).group_by(Ticket.category)
    ).all())
    return counts

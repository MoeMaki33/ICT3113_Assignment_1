import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import db
from app.database.models import Base
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = db.build_engine(f"sqlite:///{(tmp_path / 'tickets.db').as_posix()}")
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(db, "engine", engine)
    Base.metadata.create_all(engine)

    def override_db():
        with sessions() as session:
            yield session

    application = create_app(str(tmp_path / "service.log"))
    application.dependency_overrides[db.get_db] = override_db
    with TestClient(application) as test_client:
        yield test_client
    engine.dispose()

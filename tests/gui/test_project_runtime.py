"""Tests for project runtime wiring."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base
from database.models import Project
from services.project_runtime import build_project_runtime


class FakeContext:
    def __init__(self, session_factory):
        self.name = "Tower"
        self._session_factory = session_factory

    def session(self):
        return self._session_factory()


def _make_session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_building_runtime_requires_project():
    SessionLocal = _make_session_factory()
    context = FakeContext(SessionLocal)

    try:
        build_project_runtime(context)
    except ValueError as exc:
        assert "not initialized" in str(exc)
    else:  # pragma: no cover
        assert False, "Expected ValueError when project is missing"


def test_build_project_runtime_returns_service():
    SessionLocal = _make_session_factory()

    session = SessionLocal()
    session.add(Project(name="Tower"))
    session.commit()
    session.close()

    context = FakeContext(SessionLocal)
    runtime = build_project_runtime(context)

    try:
        assert runtime.project.name == "Tower"
        assert runtime.result_service is not None
    finally:
        runtime.dispose()

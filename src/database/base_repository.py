"""Shared SQLAlchemy repository helpers."""

from __future__ import annotations

from typing import Generic, Optional, Type, TypeVar

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Provides common CRUD helpers for repositories."""

    model: Type[ModelT]

    def __init__(self, session: Session):
        self.session = session

    def create(self, **kwargs) -> ModelT:
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance

    def get_by_id(self, pk: int) -> Optional[ModelT]:
        return self.session.query(self.model).filter(self.model.id == pk).first()

    def delete(self, instance: ModelT) -> None:
        self.session.delete(instance)
        self.session.commit()

    def list_all(self) -> list[ModelT]:
        return self.session.query(self.model).all()

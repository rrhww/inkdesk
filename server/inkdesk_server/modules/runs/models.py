from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from inkdesk_server.db import Base


class RunGoalContract(Base):
    __tablename__ = "run_goal_contracts"
    __table_args__ = (
        UniqueConstraint("run_id"),
        CheckConstraint("schema_version = 1", name="ck_run_goal_contracts_schema_version"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("dev_runs.id", ondelete="CASCADE"), nullable=False)
    schema_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    contract_json: Mapped[str] = mapped_column(Text, nullable=False)
    contract_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from hdfs_anomaly.app.db.base import Base


class Role(enum.StrEnum):
    ADMIN = "ADMIN"
    USER = "USER"


class Status(enum.StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Profile(Base):
    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[Status] = mapped_column(
        Enum(Status, name="status"),
        nullable=False,
        default=Status.INACTIVE,
        server_default=Status.INACTIVE.value,
    )
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="role"),
        nullable=False,
        default=Role.USER,
        server_default=Role.USER.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

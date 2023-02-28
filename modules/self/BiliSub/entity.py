from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship

from service.db import DataBase

db = DataBase(DataBase.make_sqlite_url(__file__, "bilisub.sqlite3"))


class Subscription(db.Model, table=True):
    group: int = Field(primary_key=True)
    target: int = Field(primary_key=True)
    sub_type: str = Field(primary_key=True)
    create_time: datetime = Field(default_factory=datetime.now)


class DynamicImage(db.Model, table=True):
    __table_args__ = {"sqlite_autoincrement": True}

    id: int | None = Field(default=None, primary_key=True)
    url: str
    did: int = Field(foreign_key="dynamiclog.id")


class DynamicLog(db.Model, table=True):
    id: int = Field(primary_key=True)
    type: int
    up_id: int
    up_name: str
    up_icon: str
    dyn_desc: str
    create_time: datetime

    imgs: Optional[list[DynamicImage]] = Relationship()

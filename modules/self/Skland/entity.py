from datetime import datetime

from sqlmodel import Field

from service.db import DataBase

db = DataBase(DataBase.make_sqlite_url(__file__))


class User(db.Model, table=True):
    __tablename__ = "user"  # type: ignore

    qid: int = Field(primary_key=True)
    uid: int = Field(primary_key=True)
    cred: str
    token: str | None
    name: str
    channel: str


class AttendanceLog(db.Model, table=True):
    __tablename__ = "attendance_log"  # type: ignore

    __table_args__ = {"sqlite_autoincrement": True}
    id: int | None = Field(default=None, primary_key=True)
    qid: int = Field()
    uid: int = Field()
    dtime: datetime = Field(default=datetime.now())
    # resource reward
    count: int = Field()
    rid: int = Field()
    rname: str = Field()
    rtype: str = Field()

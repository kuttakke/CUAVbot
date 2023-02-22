from datetime import date, datetime

from sqlmodel import Field

from service.db.database import DataBase

db = DataBase(DataBase.make_sqlite_url(__file__, "core.sqlite3"))
_model = db.Model


class Group(_model, table=True):
    id: int = Field(primary_key=True)
    is_block: bool = Field(default=False, index=True)


class Friend(_model, table=True):
    id: int = Field(primary_key=True)
    is_block: bool = Field(default=False, index=True)


class Modules(_model, table=True):
    __table_args__ = {"sqlite_autoincrement": True}

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    author: str | None = Field(default=None, nullable=True)
    description: str | None = Field(default=None, nullable=True)
    arg_description: str | None = Field(default=None, nullable=True)
    usage: str | None = Field(default=None, nullable=True)
    example: str | None = Field(default=None, nullable=True)
    file_name: str = Field(unique=True, index=True)
    is_enable: bool = Field(default=True)
    is_exist: bool = Field(default=True)
    create_date: date = Field(default_factory=date.today)
    update_date: date | None = Field(default_factory=date.today, nullable=True)


class BlockListMember(_model, table=True):
    group_id: int = Field(index=True, primary_key=True)
    member_id: int = Field(index=True, primary_key=True)
    module: str = Field(primary_key=True, foreign_key="modules.name")


class BlockListGroup(_model, table=True):
    group_id: int = Field(index=True, primary_key=True)
    module: str = Field(primary_key=True, foreign_key="modules.name")


class BlockListFriend(_model, table=True):
    friend_id: int = Field(index=True, primary_key=True)
    module: str = Field(primary_key=True, foreign_key="modules.name")


class ModelsCallLog(_model, table=True):
    __table_args__ = {"sqlite_autoincrement": True}

    id: int | None = Field(default=None, primary_key=True)
    group_id: int | None = Field(default=None, nullable=True)
    target_id: int
    model_name: str = Field(foreign_key="modules.name")
    create_time: datetime = Field(default_factory=datetime.now)
    as_persistent_string: str | None = Field(default=None, nullable=True)


class ChatGroupLog(_model, table=True):
    __table_args__ = {"sqlite_autoincrement": True}

    id: int | None = Field(default=None, primary_key=True)
    group_id: int = Field(index=True)
    member_id: int = Field(index=True)
    message_id: int = Field(index=True)
    create_time: datetime = Field(default_factory=datetime.now)
    as_persistent_string: str | None = Field(default=None, nullable=True)


class ChatFriendLog(_model, table=True):
    __table_args__ = {"sqlite_autoincrement": True}

    id: int | None = Field(default=None, primary_key=True)
    friend_id: int = Field(index=True)
    message_id: int = Field(index=True)
    create_time: datetime = Field(default_factory=datetime.now)
    as_persistent_string: str | None = Field(default=None, nullable=True)

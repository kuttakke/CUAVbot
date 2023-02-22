from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship

from service.db import DataBase

db = DataBase(DataBase.make_sqlite_url(__file__))


class PixivBlockTag(db.Model, table=True):
    """用户屏蔽标签"""

    __tablename__ = "pixiv_block_tag"  # type: ignore

    qq_id: int = Field(primary_key=True, foreign_key="pixiv_account.qq_id")
    tag_name: str = Field(primary_key=True)


class PixivAccount(db.Model, table=True):
    """Pixiv账号信息"""

    __tablename__ = "pixiv_account"  # type: ignore

    qq_id: int = Field(primary_key=True)
    access_token: str
    refresh_token: str
    is_active: bool = Field(default=True)
    create_date: datetime = Field(default_factory=datetime.now)

    block_tags: Optional[list["PixivBlockTag"]] = Relationship()


class PixivWorkTag(db.Model, table=True):
    """作品标签对应第三表"""

    __tablename__ = "pixiv_work_tag"  # type: ignore

    work_id: int = Field(primary_key=True, foreign_key="pixiv_work.id")
    tag_id: int = Field(primary_key=True, foreign_key="pixiv_tag.id")


class PixivTag(db.Model, table=True):
    """pixiv标签"""

    __tablename__ = "pixiv_tag"  # type: ignore
    __table_args__ = {"sqlite_autoincrement": True}

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)


class PixivUser(db.Model, table=True):
    """pixiv作者"""

    __tablename__ = "pixiv_user"  # type: ignore

    id: int = Field(primary_key=True)
    name: str = Field(index=True)
    img_path: str


class PixivMetaPage(db.Model, table=True):
    """pixiv单个作品实际url和路径"""

    __tablename__ = "pixiv_meta_page"  # type: ignore

    id: int | None = Field(default=None, primary_key=True, foreign_key="pixiv_work.id")
    page_count: int = Field(primary_key=True)
    original: str
    square_medium: str | None = Field(nullable=True)
    medium: str | None = Field(nullable=True)
    large: str | None = Field(nullable=True)
    path: str


class PixivWork(db.Model, table=True):
    """pixiv单个作品"""

    __tablename__ = "pixiv_work"  # type: ignore

    id: int = Field(primary_key=True)
    title: str = Field()
    type: str = Field()
    user_id: int = Field(foreign_key="pixiv_user.id")
    create_date: datetime = Field()
    page_count: int = Field()

    tags: Optional[list["PixivTag"]] = Relationship(link_model=PixivWorkTag)
    meta_pages: Optional[list["PixivMetaPage"]] = Relationship()
    user: Optional["PixivUser"] = Relationship()


class PixivUpdate(db.Model, table=True):
    """单个账号的更新情况"""

    __tablename__ = "pixiv_update"  # type: ignore

    account_id: int = Field(primary_key=True, foreign_key="pixiv_account.qq_id")
    work_id: int = Field(primary_key=True, foreign_key="pixiv_work.id")
    create_date: datetime = Field(default_factory=datetime.now)

import asyncio
from os import PathLike
from pathlib import Path
from typing import TypeVar, overload

from loguru import logger
from sqlalchemy.engine.result import ScalarResult
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql.dml import Delete, Insert, Update
from sqlmodel import Session, SQLModel, create_engine, delete, insert, select, update
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.main import registry
from sqlmodel.sql.base import Executable
from sqlmodel.sql.expression import Select, SelectOfScalar

__all__ = ["DataBase"]

T = TypeVar("T", bound=SQLModel)
StmtType = TypeVar(
    "StmtType", Select, Executable, Delete, Insert, Update, SelectOfScalar
)
# StmtType = Select[T] | Executable[T] | Delete | Insert | Update | SelectOfScalar[T]
_db: dict[str, "DataBase"] = {}


class DataBase:
    """面向模块化的数据库实例

    实例化数据库对象，传入数据库连接地址

    ```python
    db = DataBase("sqlite+aiosqlite:///db.sqlite3")
    ```

    创建模型类

    ```python
    class User(db.Model, table=True):
        __table_args__ = {"sqlite_autoincrement": True}

        id: int | None = Field(default=None, primary_key=True)
        name: str
        full_name: str | None = None
    ```

    创建表

    ```python
    await db.create_all()
    ```

    Args格式说明

    - `table`要求声明式(模型类)，或经过`mapper`映射的命令式(Table类)

    - `where`条件格式：`[table.column == value, table.column == value]`

    - `values`格式：`{column: value, column: value}` or `[{column: value, column: value}, ...]`

    - `stmt`格式：`insert(table).values(values)`以及类似的语句

    """

    def __init__(self, url: str, echo: bool = False) -> None:
        """创建数据库实例

        Args:
            url (str): 数据库连接地址
            echo (bool, optional): 是否打印SQL语句. Defaults to False.
        """
        self.url = url
        self.engine = create_async_engine(url, echo=echo)
        self.engine_sync = create_engine(url.replace("+aiosqlite", ""), echo=echo)
        # LINK - https://www.dazhuanlan.com/yijieshusheng/topics/1241101#expire_on_commit
        self.session = AsyncSession(self.engine, expire_on_commit=False)
        self.session_sync = Session(self.engine_sync, expire_on_commit=False)
        # LINK - https://github.com/tiangolo/sqlmodel/issues/245 动态生成SQLModel的Base类
        self.registry = registry()
        self._Model = None
        self._lock = asyncio.Lock() if self.url.startswith("sqlite") else None
        _db[self.url] = self

    @property
    def Model(self):
        if not self._Model:

            class Base(SQLModel, registry=self.registry):
                ...

            self._Model = Base
        return self._Model

    @staticmethod
    def make_sqlite_url(path: str | PathLike, name: str = "db.sqlite3") -> str:
        """生成数据库连接地址

        Args:
            path (str | PathLike): 数据库文件路径，文件名默认为db.sqlite3

        Returns:
            str: 数据库连接地址
        """
        path = Path(path)
        path = path / name if path.is_dir() else path.parent / name
        if not path.parent.exists():
            path.parent.mkdir(parents=True)
        return f"sqlite+aiosqlite:///{path}"

    async def create(self) -> None:
        """创建所有表"""
        try:
            if self._lock:
                await self._lock.acquire()
            async with self.engine.begin() as conn:
                _ = await conn.run_sync(self.Model.metadata.create_all)
        finally:
            if self._lock:
                self._lock.release()

    def create_sync(self) -> None:
        """创建所有表"""
        self.Model.metadata.create_all(self.engine_sync)

    async def remove_instance(self) -> None:
        """移除实例"""
        await self.engine.dispose()
        _db.pop(self.url)

    async def execute(self, stmt: StmtType) -> ScalarResult:
        """执行sqlalchemy语句

        Args:
            stmt (str): sqlalchemy 2.0语句
        """
        try:
            if self._lock:
                await self._lock.acquire()
            res = await self.session.exec(stmt)  # type: ignore
            await self.session.commit()
            return res
        except Exception as e:
            await self.session.rollback()
            raise e
        finally:
            if self._lock:
                self._lock.release()

    @overload
    async def add(self, table: type[T], values: dict, exist_ok: bool = True) -> T:
        ...

    @overload
    async def add(
        self, table: type[T], values: list[dict], exist_ok: bool = True
    ) -> list[T]:
        ...

    def _generate_select_where_element(self, table: type[T], values: dict):
        return [getattr(table, k) == v for k, v in values.items()]

    async def _add_one(self, table: type[T], values: dict, exist_ok: bool = True) -> T:
        where = self._generate_select_where_element(table, values)
        if not exist_ok:
            await self.execute(insert(table).values(**values))
            return await self.select_one(table, where)
        if not await self.select_one(table, where):
            await self.execute(insert(table).values(**values))
        return await self.select_one(table, where)

    async def add(
        self, table: type[T], values: dict | list[dict], exist_ok: bool = True
    ) -> T | list[T]:
        """插入数据

        Args:
            table (type[T]): 表
            values (dict | list[dict]): 数据
            exist_ok (bool, optional): 如果存在则不插入. Defaults to True.

        Returns:
            T | list[T]: 插入数据的实例
        """
        return (
            await self._add_one(table, values, exist_ok)
            if isinstance(values, dict)
            else await asyncio.gather(
                *[self._add_one(table, v, exist_ok) for v in values]
            )
        )

    async def delete(self, table: type[T], where: list):
        """删除数据

        Args:
            table (type[T]): 表
            where (list): 条件
        """
        await self.execute(delete(table).where(*where))

    @overload
    async def select_one(self, table_or_stmt: type[T], where: list) -> T:
        """查询一条数据

        Args:
            table (type[T]): 表
            where (list): 条件

        Returns:
            T: 数据
        """
        ...

    @overload
    async def select_one(
        self, table_or_stmt: SelectOfScalar[T] | Select[T], where=None
    ) -> T:
        """查询一条数据

        Args:
            stmt (str): sqlalchemy 2.0语句

        Returns:
            T: 数据
        """
        ...

    async def select_one(
        self, table_or_stmt: SelectOfScalar[T] | type[T] | Select[T], where=None
    ) -> T | None:
        stmt: SelectOfScalar = select(table_or_stmt).where(*where) if where else table_or_stmt  # type: ignore
        res = await self.execute(stmt.limit(1))
        return res.one_or_none()

    @overload
    async def select(self, table_or_stmt: type[T], where: list) -> list[T]:
        ...

    @overload
    async def select(self, table_or_stmt: SelectOfScalar[T], where=None) -> list[T]:
        ...

    async def select(
        self, table_or_stmt: SelectOfScalar[T] | type[T], where=None
    ) -> list[T]:
        """查询多条数据

        Args:
            stmt (str): sqlalchemy 2.0语句

        Returns:
            list[T]: 数据实体列表
        """
        stmt: SelectOfScalar = select(table_or_stmt).where(*where) if where else table_or_stmt  # type: ignore
        res = await self.execute(stmt)
        return res.all()

    def select_one_sync(self, table: type[T], where=None) -> T | None:
        """同步查询一条数据

        Args:
            table (type[T]): 表
            where (list): 条件

        Returns:
            T: 数据
        """
        if where is None:
            where = []
        return self.session_sync.exec(select(table).where(*where)).one_or_none()

    def select_sync(self, table: type[T], where: list | None = None) -> list[T]:
        """同步查询多条数据，仅用于初始化模块

        Args:
            table (type[T]): 表
            where (list, optional): 条件. Defaults to None.

        Returns:
            list[T]: 数据实体列表
        """
        if where is None:
            where = []
        return self.session_sync.exec(select(table).where(*where)).all()

    async def update(
        self,
        table: type[T],
        values: dict | list[dict],
        where: list | None = None,
        or_create: bool = False,
    ):
        """更新数据

        Args:
            table (type[T]): 表
            values (dict | list[dict]): 数据
            where (list | None): 条件
            or_create (bool): 如果不存在则创建
        """
        if where is None:
            where = []
        if or_create:
            if not where:
                raise ValueError("where elements can not be empty")
            if not await self.select_one(table, where):
                await self.add(table, values)
                return
        await self.execute(update(table).values(**values).where(*where)) if isinstance(
            values, dict
        ) else await self.execute(update(table).values(values).where(*where))

    def update_sync(
        self,
        table: type[T],
        values: dict,
        where: list | None = None,
        or_create: bool = False,
    ):
        """同步更新数据

        Args:
            table (type[T]): 表
            values (dict): 数据
            where (list): 条件
            or_create (bool): 如果不存在则创建
        """
        if where is None:
            where = []
        if or_create:
            if not where:
                raise ValueError("where elements can not be empty")
            if not self.select_one_sync(table, where):
                self.session_sync.exec(insert(table).values(**values))  # type: ignore
                self.session_sync.commit()
                return
        self.session_sync.exec(update(table).values(**values).where(*where))  # type: ignore
        self.session_sync.commit()

    @classmethod
    async def create_all(cls):
        """创建所有已创建实例的数据库"""
        await asyncio.gather(*[db.create() for db in _db.values()])
        logger.info(f"create {len(_db)} database table")

    @classmethod
    async def showdown(cls):
        """关闭所有实例链接"""
        await asyncio.gather(*[db.engine.dispose() for db in _db.values()])
        logger.info(f"{len(_db)} database showdown complete")

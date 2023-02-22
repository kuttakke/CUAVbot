from datetime import datetime
from typing import Any

from sqlalchemy.orm import selectinload
from sqlmodel import col, func, select

from .entity import (
    PixivAccount,
    PixivBlockTag,
    PixivMetaPage,
    PixivTag,
    PixivUpdate,
    PixivUser,
    PixivWork,
    PixivWorkTag,
    db,
)


class Curd:
    @staticmethod
    async def get_pixiv_account_by_qqid(qq_id: int) -> PixivAccount | None:
        """根据qq号获取pixiv账号"""
        return await db.select_one(PixivAccount, [PixivAccount.qq_id == qq_id])

    @staticmethod
    async def get_all_pixiv_account() -> list[PixivAccount]:
        """获取所有pixiv账号"""
        stmt = select(PixivAccount).options(selectinload(PixivAccount.block_tags))
        return await db.select(stmt)

    @staticmethod
    async def get_pixiv_work_by_id(
        pid: int, load_child: bool = False
    ) -> PixivWork | None:
        """根据作品id获取作品"""
        stmt = select(PixivWork).where(PixivWork.id == pid).limit(1)
        if load_child:
            stmt = stmt.options(
                selectinload(PixivWork.user),
                selectinload(PixivWork.tags),
                selectinload(PixivWork.meta_pages),
            )
        return await db.select_one(stmt)

    @staticmethod
    async def get_pixiv_block_tag_by_qqid_and_name(
        qq_id: int, name: str
    ) -> PixivBlockTag | None:
        """根据qq号和标签名获取屏蔽标签"""
        return await db.select_one(
            PixivBlockTag,
            [PixivBlockTag.qq_id == qq_id, PixivBlockTag.tag_name == name],
        )

    @staticmethod
    async def get_pixiv_works_by_id_list(id_list: list[int]) -> list[PixivWork]:
        """根据作品id列表获取作品"""
        stmt = select(PixivWork).where(col(PixivWork.id).in_(id_list))
        return await db.select(stmt)

    @staticmethod
    async def get_pixiv_update_by_qqid_and_work_id_list(
        qq_id: int, work_id_list: list[int]
    ) -> list[PixivUpdate]:
        """根据qq号和作品id列表获取更新记录"""
        stmt = (
            select(PixivUpdate)
            .where(
                col(PixivUpdate.account_id) == qq_id,
                col(PixivUpdate.work_id).in_(work_id_list),
            )
            .limit(len(work_id_list))
        )
        return await db.select(stmt)

    @staticmethod
    async def get_pixiv_user_by_id(uid: int) -> PixivUser | None:
        """根据作者id获取作者"""
        return await db.select_one(PixivUser, [PixivUser.id == uid])

    @staticmethod
    async def get_pixiv_user_by_id_list(id_list: list[int]) -> list[PixivUser]:
        """根据作者id列表获取作者"""
        stmt = select(PixivUser).where(col(PixivUser.id).in_(id_list))
        return await db.select(stmt)

    @staticmethod
    async def get_pixiv_tag_by_name(name: str) -> PixivTag | None:
        """根据标签名获取标签"""
        return await db.select_one(PixivTag, [PixivTag.name == name])

    @staticmethod
    async def get_pixiv_tags_by_name_list(name_list: list[str]) -> list[PixivTag]:
        """根据标签名列表获取标签"""
        stmt = select(PixivTag).where(col(PixivTag.name).in_(name_list))
        return await db.select(stmt)

    @staticmethod
    async def get_pixiv_update_work_and_page_num(qq_id: int) -> tuple[int, int]:
        """获取更新作品和页数"""
        work_count = await db.execute(
            select(func.count(PixivUpdate.work_id)).where(PixivUpdate.account_id == qq_id)  # type: ignore
        )
        page_count = await db.execute(
            select(func.count(PixivMetaPage.id))  # type: ignore
            .where(PixivMetaPage.id == PixivUpdate.work_id)
            .outerjoin(PixivUpdate, PixivUpdate.account_id == qq_id)
        )
        return work_count.one(), page_count.one()

    @staticmethod
    async def insert_pixiv_account(
        qq_id: int,
        access_token: str,
        refresh_token: str,
        create_date: datetime | None = None,
    ):
        """插入pixiv账号"""
        await db.add(
            PixivAccount,
            values={
                "qq_id": qq_id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "create_date": create_date or datetime.now(),
            },
        )

    @staticmethod
    async def insert_pixiv_user(user: PixivUser):
        """插入pixiv作者"""
        await db.add(PixivUser, values=user.dict())

    @staticmethod
    async def insert_pixiv_block_tag(qq_id: int, tag_name: str):
        """插入pixiv屏蔽标签"""
        await db.add(
            PixivBlockTag,
            values={
                "qq_id": qq_id,
                "tag_name": tag_name,
            },
        )

    @staticmethod
    async def insert_pixiv_tag(name: str) -> PixivTag:
        """插入pixiv标签"""
        return await db.add(PixivTag, values={"name": name})

    @staticmethod
    async def insert_pixiv_work(work: PixivWork, qq_id: int):
        """插入pixiv作品"""
        assert work.meta_pages
        assert work.tags is not None
        await db.add(
            PixivWork, values=work.dict(exclude={"user", "tags", "meta_pages"})
        )
        await db.add(PixivMetaPage, values=[i.dict() for i in work.meta_pages])
        await db.add(
            PixivWorkTag,
            values=[{"work_id": work.id, "tag_id": tag.id} for tag in work.tags],
        )
        await db.add(
            PixivUpdate,
            values={
                "account_id": qq_id,
                "work_id": work.id,
            },
        )

    @staticmethod
    async def update_pixiv_account(qq_id: int, data: dict[str, Any]):
        """更新pixiv账号"""
        await db.update(PixivAccount, data, [PixivAccount.qq_id == qq_id])

    @staticmethod
    async def delete_pixiv_account(qq_id: int):
        """删除pixiv账号"""
        await db.delete(PixivAccount, [PixivAccount.qq_id == qq_id])

    @staticmethod
    async def delete_pixiv_block_tag(qq_id: int, tag_name: str):
        """删除pixiv屏蔽标签"""
        await db.delete(
            PixivBlockTag,
            [PixivBlockTag.qq_id == qq_id, PixivBlockTag.tag_name == tag_name],
        )

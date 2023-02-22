import os
import pkgutil
from datetime import datetime
from pathlib import Path

from graia.ariadne.entry import Ariadne, Saya
from graia.saya.channel import Channel
from loguru import logger
from sqlmodel import select

from config import settings

from .entity import (
    BlockListFriend,
    BlockListGroup,
    BlockListMember,
    ChatGroupLog,
    Modules,
    db,
)


class Controller:
    db = db
    saya: Saya

    @classmethod
    def _require(cls, modules: list[str], is_core: bool = False):
        all_disabled_modules = (
            []
            if is_core
            else [
                i.file_name
                for i in cls.db.select_sync(Modules, where=[Modules.is_enable == False])
            ]
        )
        with cls.saya.module_context():
            for module in modules:
                if module in all_disabled_modules:
                    continue
                path = (
                    f"{settings.mirai.modules_base_path}."
                    f"{settings.mirai.core_modules_path if is_core else settings.mirai.self_modules_path}."
                    f"{module}"
                )
                cls.saya.require(path)

    @classmethod
    def module_register(cls, module: Modules) -> Channel:
        channel = Channel.current()
        channel.name(module.name)
        channel.meta["author"] = module.author
        channel.description(module.description)  # type: ignore
        if md := cls.db.select_one_sync(
            Modules, where=[Modules.file_name == module.file_name]
        ):
            exclude = {"id", "create_date", "update_date"}
            if md.dict(exclude=exclude) != module.dict(exclude=exclude):
                logger.debug(f"Module {module.name} has been updated.")
                cls.db.update_sync(
                    Modules,
                    values=module.dict(exclude={"id", "create_date"}),
                    where=[Modules.file_name == module.file_name],
                )
            return channel
        logger.debug(f"Module {module.name} has been registered.")
        cls.db.update_sync(
            Modules,
            values=module.dict(exclude={"id"}),
            where=[Modules.file_name == module.file_name],
            or_create=True,
        )
        return channel

    @classmethod
    def load_modules(cls):
        cls.db.create_sync()
        base_modules_path = Path(os.getcwd(), settings.mirai.modules_base_path)
        cls._require(
            [
                i.name
                for i in pkgutil.iter_modules(
                    [str(base_modules_path / settings.mirai.core_modules_path)]
                )
            ],
            True,
        )
        if settings.mirai.debug_module:
            cls._require(settings.mirai.debug_module)
            return
        need_load_modules = base_modules_path / settings.mirai.self_modules_path
        cls._require([i.name for i in pkgutil.iter_modules([str(need_load_modules)])])

    @classmethod
    def install_modules(cls, file_name: str):
        try:
            with cls.saya.module_context():
                cls.saya.require(
                    f"{settings.mirai.modules_base_path}."
                    f"{settings.mirai.self_modules_path}."
                    f"{file_name}"
                )
        except Exception as e:
            return f"安装失败: {e}"
        return "安装成功"

    @classmethod
    def uninstall_modules(cls, file_name: str):
        try:
            channel = cls.saya.channels.get(
                f"{settings.mirai.modules_base_path}."
                f"{settings.mirai.self_modules_path}."
                f"{file_name}"
            )
            if not channel:
                return "卸载失败：未找到该模块"
            with cls.saya.module_context():
                cls.saya.uninstall_channel(channel)
        except Exception as e:
            return f"卸载失败: {e}"
        cls.db.update_sync(
            Modules, values={"is_enable": False}, where=[Modules.file_name == file_name]
        )
        return "卸载成功"

    @classmethod
    def reload_modules(cls, file_name: str):
        try:
            channel = cls.saya.channels.get(
                f"{settings.mirai.modules_base_path}."
                f"{settings.mirai.self_modules_path}."
                f"{file_name}"
            )
            if not channel:
                return "重载失败：未找到该模块"
            with cls.saya.module_context():
                cls.saya.reload_channel(channel)
        except Exception as e:
            return f"重载失败: {e}"
        return "重载成功"

    @classmethod
    async def is_block(cls, name: str, group: int, member: int | None = None) -> bool:
        if member:
            return bool(
                await cls.db.select_one(
                    BlockListMember,
                    where=[
                        BlockListMember.module == name,
                        BlockListMember.group_id == group,
                        BlockListMember.member_id == member,
                    ],
                )
            )
        return bool(
            await cls.db.select_one(
                BlockListGroup,
                where=[
                    BlockListGroup.module == name,
                    BlockListGroup.group_id == group,
                ],
            )
        )

    @classmethod
    async def is_block_friend(cls, name: str, friend: int) -> bool:
        return bool(
            await cls.db.select_one(
                BlockListFriend,
                where=[
                    BlockListFriend.module == name,
                    BlockListFriend.friend_id == friend,
                ],
            )
        )

    @classmethod
    async def unban_member(cls, name: str, group: int, member: int):
        await cls.db.delete(
            BlockListMember,
            where=[
                BlockListMember.module == name,
                BlockListMember.group_id == group,
                BlockListMember.member_id == member,
            ],
        )

    @classmethod
    async def unban_group(cls, name: str, group: int):
        await cls.db.delete(
            BlockListGroup,
            where=[
                BlockListGroup.module == name,
                BlockListGroup.group_id == group,
            ],
        )

    @classmethod
    async def ban_member(cls, name: str, group: int, member: int):
        await cls.db.add(
            BlockListMember,
            values={"module": name, "group_id": group, "member_id": member},
            exist_ok=True,
        )

    @classmethod
    async def ban_group(cls, name: str, group: int):
        await cls.db.add(
            BlockListGroup,
            values={"module": name, "group_id": group},
            exist_ok=True,
        )

    @classmethod
    def get_module_name_by_index(cls, index: int) -> str | None:
        if index > len(cls.saya.channels) or index < 1:
            return None
        return list(cls.saya.channels.values())[index - 1].meta["name"]

    @classmethod
    async def get_file_path_by_name(cls, name: str) -> str:
        module = await cls.db.select_one(Modules, where=[Modules.name == name])
        return module.file_name if module else ""

    @classmethod
    async def get_module_by_name(cls, name: str) -> Modules | None:
        return await cls.db.select_one(Modules, where=[Modules.name == name])

    @classmethod
    async def get_block_member_list(
        cls, name: str, group: int
    ) -> list[BlockListMember]:
        return await cls.db.select(
            BlockListMember,
            where=[
                BlockListMember.module == name,
                BlockListMember.group_id == group,
            ],
        )

    @classmethod
    async def get_member_name(cls, group: int, member: int) -> str | None:
        try:
            member_info = await Ariadne.current().get_member(group, member)
        except Exception as e:
            logger.exception(e)
            return None
        return member_info.name

    @classmethod
    async def get_block_list(cls, group: int) -> list[BlockListGroup]:
        return await cls.db.select(
            BlockListGroup,
            where=[BlockListGroup.group_id == group],
        )

    @classmethod
    async def get_chat_group_log(
        cls, group: int, member: int, date: datetime | None = None
    ) -> list[ChatGroupLog]:
        stmt = select(ChatGroupLog).where(
            ChatGroupLog.group_id == group, ChatGroupLog.member_id == member
        )
        if date:
            stmt = stmt.where(ChatGroupLog.create_time >= date)
        res = await cls.db.execute(stmt)
        return res.all()

    @classmethod
    def run(cls):
        try:
            from graia.ariadne.entry import (
                HttpClientConfig,
                WebsocketClientConfig,
                config,
            )
            from graia.saya.builtins.broadcast import BroadcastBehaviour
            from graia.scheduler import GraiaScheduler
            from graia.scheduler.saya import GraiaSchedulerBehaviour
            from graiax.playwright import PlaywrightService

            from config import settings
            from service.db import DataBaseService
            from utils.logger_rewrite import (
                rewrite_ariadne_logger,
                rewrite_logging_logger,
            )
        except Exception as e:
            import traceback

            traceback.print_exc()
            input("导入错误，已阻塞")
            raise e

        app = Ariadne(
            config(
                settings.mirai.account,  # 你的机器人的 qq 号
                settings.mirai.key,  # 填入 verifyKey
                HttpClientConfig(host=settings.mirai.host),
                WebsocketClientConfig(host=settings.mirai.host),
            )
        )  # 填入 http-api 服务运行的地址
        saya = app.create(Saya)
        cls.saya = saya
        app.create(GraiaScheduler)
        saya.install_behaviours(
            app.create(BroadcastBehaviour), app.create(GraiaSchedulerBehaviour)
        )
        app.launch_manager.add_service(PlaywrightService(headless=True))
        app.launch_manager.add_service(DataBaseService())
        rewrite_ariadne_logger(True, False)  # 对logger进行调整，必须放在这里
        rewrite_logging_logger("peewee")
        try:
            cls.load_modules()
        except BaseException as e:
            import traceback

            traceback.print_exc()
            input("启动错误，进行阻塞")
            raise e
        app.launch_blocking()

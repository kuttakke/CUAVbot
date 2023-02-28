import asyncio
from typing import Literal

from bilireq.exceptions import ResponseCodeError
from bilireq.utils import get
from graia.ariadne.message.chain import MessageChain
from loguru import logger

from .service import (
    add_subscription,
    get_all_subscription,
    get_subscription,
    get_subscription_by_group,
    remove_subscription,
)
from .sub import Sub


# TODO - 无法截图还需优化
class SubCtrl:
    _sub_list: list[Sub] = []
    _listen_dynamic_list = []

    @classmethod
    async def init(cls):
        for sub in await get_all_subscription():
            if sub.target in cls._listen_dynamic_list:
                continue
            cls._sub_list.append(Sub(sub.target, sub.sub_type))  # type: ignore
            cls._listen_dynamic_list.append(sub.target)
        logger.success(f"['Bili订阅']已加载{len(cls._sub_list)}个订阅")

    @classmethod
    async def name_by_uid(cls, uid: int) -> str:  # type: ignore
        try:
            data = await get(f"https://api.bilibili.com/x/space/acc/info?mid={uid}")
        except ResponseCodeError:
            return ""
        return data["name"]

    @classmethod
    async def add(
        cls, group: int, target: int, sub_type: Literal["dynamic", "live"] = "dynamic"
    ) -> MessageChain:
        name = await cls.name_by_uid(target)
        if not name:
            return MessageChain("未找到此用户哦~")
        if await get_subscription(group, target, sub_type):
            return MessageChain("此订阅已存在哦~")
        if target not in cls._listen_dynamic_list:
            sub_ = Sub(target, sub_type)
            cls._sub_list.append(sub_)
            await sub_.run()
            cls._listen_dynamic_list.append(target)
        await add_subscription(group, target, sub_type)
        logger.success(f"['Bili订阅']已添加订阅{name}({target})({sub_type})")
        return MessageChain(f"订阅{name}({target})成功~")

    @classmethod
    async def remove(
        cls, group: int, target: int, sub_type: Literal["dynamic", "live"] = "dynamic"
    ) -> MessageChain:
        sub = await get_subscription(group, target, sub_type)
        if not sub:
            return MessageChain("此订阅不存在哦~")
        cls._sub_list.remove(Sub(sub.target, sub.sub_type))  # type: ignore
        if all(i.target != sub.target for i in cls._sub_list):
            cls._listen_dynamic_list.remove(sub.target)
        await remove_subscription(group, target, sub_type)
        logger.success(f"['Bili订阅']已删除订阅{target}({sub_type})")
        name = await cls.name_by_uid(target)
        return MessageChain(f"取消订阅{name}({target})成功~")

    @classmethod
    async def sub_status(cls, group: int) -> MessageChain:
        subs = await get_subscription_by_group(group)
        if not subs:
            return MessageChain("暂无订阅哦~")
        msg = "当前订阅列表：\n"
        for sub in subs:
            name = await cls.name_by_uid(sub.target)
            msg += f"{name}({sub.target})\n"
        return MessageChain(msg.strip())

    @classmethod
    async def run(cls):
        _ = await asyncio.gather(*[sub.run() for sub in cls._sub_list])

import time
from pathlib import Path

from graia.ariadne.entry import (
    Ariadne,
    At,
    Group,
    GroupMessage,
    MatchResult,
    Member,
    MessageChain,
    MessageEvent,
    Plain,
    Source,
)
from graia.ariadne.event.lifecycle import ApplicationLaunched
from graia.ariadne.util.interrupt import FunctionWaiter
from graiax.shortcut.saya import decorate, dispatch, listen

from core.control import Controller
from core.depend.blacklist import BlackList
from core.entity import Modules
from utils.tool import to_module_file_name

from .Clock import ClockController
from .command import Command

module_name = "群闹钟"

module = Modules(
    name=module_name,
    author="Kutake",
    description="到点就在群里提醒，群监工desu",
    usage="""
    .闹钟 X小时|X分钟|X秒后 提醒内容(可选)

    .闹钟 今天|明天|后天+X点X分X秒 提醒内容(可选)

    ！！！可以使用回复的形式触发！！！
    """,
    example="""
    闹钟 3分钟后 检查群友状态

    闹钟 明天18点 开黑时间嗷
    """,
    file_name=to_module_file_name(Path(__file__)),
)

channel = Controller.module_register(module)


@listen(GroupMessage)
@dispatch(Command.Time)
@decorate(BlackList.require(module_name))
async def add_task(
    group: Group,
    member: Member,
    msg: MessageChain,
    event: MessageEvent,
    source: Source,
    cmd: MatchResult,
):
    source_id = event.quote.id if event.quote else source.id
    await ClockController.add_task(
        group.id, member.id, source_id, time.time(), cmd.result.display  # type: ignore
    )


@listen(GroupMessage)
@dispatch(Command.Remove)
@decorate(BlackList.require(module_name))
async def remove_cmd(app: Ariadne, group: Group, member: Member, cmd: MatchResult):
    if not (task_info := ClockController.tasks_info(group.id, member.id)):
        await app.send_group_message(
            group, MessageChain([At(member), Plain("没找到任何闹钟哦🤨")])
        )
        return
    if len(msg := cmd.result.display.split()) == 1:  # type: ignore
        if task_info[4:6] == "1个":
            await app.send_group_message(
                group, MessageChain([At(member), Plain("只有一个闹钟🤨，请回复 确定|取消 来确认")])
            )

            async def waiter(
                waiter_group: Group, waiter_member: Member, waiter_message: MessageChain
            ):
                if all(
                    [
                        waiter_group.id == group.id,
                        waiter_member.id == member.id,
                        (msg_r := waiter_message.display.strip()) in ["确定", "取消"],
                    ]
                ):
                    return "确定" == msg_r

            res = await FunctionWaiter(waiter, [GroupMessage]).wait(timeout=15)
            if res:
                await ClockController.cancel_task(
                    ClockController.get_task(group.id, member.id)  # type: ignore
                )
                await app.send_group_message(
                    group, MessageChain([At(member), Plain("闹钟取消成功🥳")])
                )
                return
            await app.send_group_message(
                group, MessageChain([At(member), Plain("取消本操作")])
            )
            return
        await app.send_group_message(
            group,
            MessageChain([At(member), Plain(task_info), Plain("\n请加上对应闹钟的数字再次请求删除😘")]),
        )
        return
    if not (task := ClockController.get_task(group.id, member.id, int(msg[1]) - 1)):
        await app.send_group_message(
            group, MessageChain([At(member), Plain("没有找到这个闹钟诶😕")])
        )
        return
    await ClockController.cancel_task(task)
    await app.send_group_message(group, MessageChain([At(member), Plain("闹钟取消成功🥳")]))


@listen(ApplicationLaunched)
async def init():
    await ClockController.init()


@listen(GroupMessage)
@dispatch(Command.Check)
@decorate(BlackList.require(module_name))
async def check_task(app: Ariadne, group: Group, member: Member):
    if not (task_info := ClockController.tasks_info(group.id, member.id)):
        await app.send_group_message(
            group, MessageChain([At(member), Plain("没找到任何闹钟哦🤨")])
        )
        return
    await app.send_group_message(group, MessageChain([At(member), Plain(task_info)]))

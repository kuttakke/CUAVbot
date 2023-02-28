from pathlib import Path

from graia.ariadne.entry import (
    ApplicationLaunch,
    Ariadne,
    Group,
    GroupMessage,
    MatchResult,
)
from graia.ariadne.message.parser.twilight import SpacePolicy
from graia.ariadne.util.interrupt import FunctionWaiter
from graiax.shortcut.saya import (
    decorate,
    dispatch,
    every_custom_seconds,
    listen,
    schedule,
)
from loguru import logger

from core.control import Controller
from core.depend.blacklist import BlackList
from core.entity import Modules
from utils.tool import to_module_file_name

from .command import Command
from .subctrl import SubCtrl

module_name = "B站订阅"

module = Modules(
    name=module_name,
    author="Kutake",
    description="目前仅支持动态订阅，后续可能会加入直播订阅",
    usage="""
    .订阅动态 <uid>
    
    .取消订阅动态 <uid>
    
    .订阅列表
    """,
    file_name=to_module_file_name(Path(__file__)),
)
channel = Controller.module_register(module)


@listen(GroupMessage)
@dispatch(Command.DynamicSub)
async def dynamic_sub(app: Ariadne, group: Group, uid: MatchResult):
    upid = int(uid.result.display.strip())  # type: ignore
    await app.send_message(group, await SubCtrl.add(group.id, upid))


@listen(GroupMessage)
@dispatch(Command.DynamicUnSub)
async def dynamic_unsub(app: Ariadne, group: Group, uid: MatchResult):
    upid = int(uid.result.display.strip())  # type: ignore
    await app.send_message(group, await SubCtrl.remove(group.id, upid))


@listen(GroupMessage)
@dispatch(Command.SubList)
async def dynamic_list(app: Ariadne, group: Group):
    await app.send_message(group, await SubCtrl.sub_status(group.id))


@schedule(every_custom_seconds(20))
async def run():
    # logger.info("BiliSub: run")
    await SubCtrl.run()


@listen(ApplicationLaunch)
async def init():
    await SubCtrl.init()

from pathlib import Path

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import (
    Friend,
    FriendMessage,
    Group,
    GroupMessage,
    MessageChain,
    MessageEvent,
)
from graia.ariadne.message.parser.twilight import MatchResult, RegexMatch, Twilight
from graia.saya import Channel
from graiax.shortcut.saya import decorate, dispatch, listen

from core.control import Controller, Modules
from core.depend.blacklist import BlackList
from utils.msgtool import send_forward_msg_with_retry
from utils.tool import to_module_file_name

from .lolicon import LoliconApi

module_name = "随机Pixiv图片"

module = Modules(
    name=module_name,
    file_name=to_module_file_name(Path(__file__)),
    author="Kutake",
    description="根据api.lolicon.app获取随机Pixiv图片",
    usage=".setu 或 .涩图",
    example=(
        ".setu 2 loli|少女\n\n"
        ".setu 2 loli&少女\n\n"
        ".setu 2 loli|少女&白丝|黑丝\n\n"
        "↑↑指 两张 loli或少女 的 白丝或黑丝 图片↑↑\n\n"
        "来2张涩图\n\n"
        "来5张loli的涩图\n\n"
        "所有命令setu与涩图都可替换\n\n"
        "语义化搜索不支持多个tag查询\n\n"
        "结果只支持1-9张\n\n"
        "目前仅命令式搜索支持多个tag进行AndOr查询，视查询的tag，结果有可能不足x张"
    ),
)

channel = Controller.module_register(module)

SetuSemantic = Twilight(
    [RegexMatch(r"^来[1-9一二两三四五六七八九⑨]?张([\S+]*的)?((setu)|(涩图)|(色图))\s?$") @ "match"]
)
Setu = Twilight([RegexMatch(r"^[.!！。]((setu)|(涩图)|(色图))[\s\S]*") @ "match"])


@listen(GroupMessage, FriendMessage)
@dispatch(SetuSemantic)
@decorate(BlackList.require(module_name))
async def get_setu_semantic(app: Ariadne, match: MatchResult, event: MessageEvent):
    await app.send_message(event, MessageChain("正在搜索..."))
    await send(event, await LoliconApi.run(match.result.display))  # type: ignore


@listen(GroupMessage, FriendMessage)
@dispatch(Setu)
@decorate(BlackList.require(module_name))
async def get_setu(app: Ariadne, match: MatchResult, event: MessageEvent):
    await app.send_message(event, MessageChain("正在搜索..."))
    nsfw = 2 if isinstance(event, FriendMessage) else 0
    await send(group, await LoliconApi.run(match.result.display, nsfw=nsfw, semantic=False))  # type: ignore


async def send(target: MessageEvent, msg: MessageChain):
    res = await send_forward_msg_with_retry(target, msg)
    app = Ariadne.current()
    if res.id < 0:
        await app.send_message(target, MessageChain("发送失败，可能和谐了"))

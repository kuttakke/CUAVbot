from pathlib import Path

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import (
    FriendMessage,
    GroupMessage,
    MessageChain,
    MessageEvent,
)
from graia.ariadne.message.element import Forward, Source
from graia.ariadne.message.parser.twilight import (
    MatchResult,
    RegexMatch,
    SpacePolicy,
    Twilight,
    WildcardMatch,
)
from graiax.shortcut.saya import decorate, dispatch, listen

from core.control import Controller, Modules
from core.depend.blacklist import BlackList
from utils.tool import to_module_file_name

from .Nyaa import Nyaa

module_name = "搜种"

module = Modules(
    name=module_name,
    file_name=to_module_file_name(Path(__file__)),
    author="Kutake",
    description="依靠Nyaa.sukebe站并以Rss的方式搜NSFW种",
    usage=".搜种 关键词",
)

channle = Controller.module_register(module)

SearcherCmd = Twilight(
    [
        RegexMatch(r"^[.!。！]?搜种").space(SpacePolicy.FORCE),
        WildcardMatch(greed=False) @ "text",
    ]
)


@listen(GroupMessage, FriendMessage)
@dispatch(SearcherCmd)
@decorate(BlackList.require(module_name))
async def nyaa_sukebe_search(
    app: Ariadne, event: MessageEvent, text: MatchResult, source: Source
):
    try:
        msg = await Nyaa.run(key_word=text.result.display.strip())  # type: ignore
    except Exception as e:
        await app.send_message(event, MessageChain(f"搜种出现错误: {e}"), quote=source)
        return
    if Forward not in msg:
        await app.send_message(event, msg, quote=source)
        return
    await app.send_message(event, msg)

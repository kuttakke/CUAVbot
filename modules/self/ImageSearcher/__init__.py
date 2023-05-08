import contextlib
from pathlib import Path

from graia.ariadne.entry import (
    Ariadne,
    FriendMessage,
    GroupMessage,
    Image,
    MessageChain,
    MessageEvent,
)
from graia.ariadne.exception import UnknownTarget
from graia.ariadne.message.parser.twilight import MatchResult
from graia.ariadne.util.interrupt import FunctionWaiter
from graiax.shortcut.saya import decorate, dispatch, listen

from core.control import Controller, Modules
from core.depend.blacklist import BlackList
from utils.tool import to_module_file_name

from .command import Command
from .searcher import Searcher

module_name = "聚合搜图"

module = Modules(
    name=module_name,
    file_name=to_module_file_name(Path(__file__)),
    author="Kutake",
    description="使用各种搜图引擎进行搜图",
    usage=".搜图 [图片]\n\n.百度搜图 [图片]\n\n以上可以配合回复含有图片的消息使用",
)
channel = Controller.module_register(module)


@listen(GroupMessage, FriendMessage)
@dispatch(Command.Default)
@decorate(BlackList.require(module_name))
async def waifu_group(
    app: Ariadne,
    event: MessageEvent,
    img: MatchResult,
):
    msg = event.message_chain.display
    if "百度" in msg or "谷歌" in msg:
        search = Searcher.google_baidu
    elif "二次元" in msg:
        search = Searcher.waifu
    else:
        search = Searcher.waifu
    if url := await get_url(event, img):
        await app.send_message(event, MessageChain("正在搜索中..."))
        res = await app.send_message(event, await search(url))
        if res.id < 0:
            await app.send_message(event, MessageChain("搜图结果发送失败😢可能被风控了"))
        return
    await app.send_message(event, MessageChain("请发送图片"))

    async def waiter(
        waiter_event: MessageEvent, waiter_message: MessageChain
    ) -> str | None:
        if isinstance(waiter_event, GroupMessage) and isinstance(event, GroupMessage):
            if (
                waiter_event.sender.group.id == event.sender.group.id
                and waiter_event.sender.id == event.sender.id
                and waiter_message.has(Image)
            ):
                return waiter_message.get_first(Image).url
        elif isinstance(waiter_event, FriendMessage) and isinstance(
            event, FriendMessage
        ):
            if waiter_event.sender.id == event.sender.id and waiter_message.has(Image):
                return waiter_message.get_first(Image).url

    res = await FunctionWaiter(waiter, [GroupMessage, FriendMessage]).wait(timeout=30)
    if not res:
        await app.send_message(event, MessageChain("搜图超时😢"))
        return
    await app.send_message(event, MessageChain("正在搜索中..."))
    res = await app.send_message(event, await search(res))
    if res.id < 0:
        await app.send_message(event, MessageChain("搜图结果发送失败😢可能被风控了"))


async def get_url(event: MessageEvent, img: MatchResult) -> str:
    with contextlib.suppress(UnknownTarget):
        if event.quote and (
            msg := (
                await Ariadne.current().get_message_from_id(
                    message=event.quote.id,
                )
            ).message_chain
        ).has(Image):
            return msg.get_first(Image).url  # type: ignore
    return img.result.url if img.matched else ""  # type: ignore

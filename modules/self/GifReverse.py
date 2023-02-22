import io
from asyncio import to_thread
from pathlib import Path

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, GroupMessage, Member, MessageEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Image, Plain
from graia.ariadne.message.parser.twilight import (
    ElementMatch,
    RegexMatch,
    SpacePolicy,
    Twilight,
)
from graia.ariadne.util.interrupt import FunctionWaiter
from graiax.shortcut.saya import decorate, dispatch, listen
from loguru import logger
from PIL import Image as img
from PIL import ImageSequence

from core.control import Controller, Modules
from core.depend.blacklist import BlackList
from utils.session import Session
from utils.tool import to_module_file_name

module_name = "GIF倒放"
module = Modules(
    name=module_name,
    file_name=to_module_file_name(Path(__file__)),
    author="Kutake",
    description=".reverse | .反转 | .倒放",
)
channel = Controller.module_register(module)

Searcher = Twilight(
    [
        ElementMatch(At, optional=True).space(SpacePolicy.PRESERVE),
        RegexMatch(r"[.。!！](反转|reverse|倒放)\s?").space(SpacePolicy.PRESERVE),
        ElementMatch(Image, optional=True).space(SpacePolicy.PRESERVE) @ "img",
    ]
)


class NotAGif(Exception):
    pass


async def get_url(event: MessageEvent) -> str:
    if event.quote and (
        msg := (
            await Ariadne.current().get_message_from_id(
                message=event.quote.id,
            )
        ).message_chain
    ).has(Image):
        return msg.get_first(Image).url  # type: ignore
    return ""


@listen(GroupMessage)
@dispatch(Searcher)
@decorate(BlackList.require(module_name))
async def gif_reverse(
    app: Ariadne,
    message: MessageChain,
    group: Group,
    member: Member,
    event: MessageEvent,
):
    if event.quote:
        url = await get_url(event)
    elif message.has(Image):
        url = message.get_first(Image).url
    else:

        async def waiter(waiter_group: Group, waiter_member: Member, waiter_message: MessageChain) -> str:  # type: ignore
            if (
                waiter_group.id == group.id
                and waiter_member.id == member.id
                and waiter_message.has(Image)
            ):
                return waiter_message.get(Image)[0].url  # type: ignore

        url = await FunctionWaiter(waiter, [GroupMessage]).wait(timeout=30)

    if not url:
        await app.send_group_message(group, MessageChain([Plain("取消反转")]))
        return
    await app.send_group_message(group, MessageChain([Plain("正在反转...")]))
    try:
        await app.send_group_message(
            group, MessageChain([Image(data_bytes=await _reverse_gif(url))])
        )
    except Exception as e:
        logger.exception(e)
        await app.send_group_message(group, MessageChain([Plain(f"反转失败:{e}")]))


def _check_gif(b: bytes) -> bool:
    # check 32 bytes to see if it's a gif
    return b[:6] in [b"GIF89a", b"GIF87a"]


def _reverse(b: bytes) -> bytes:
    out = io.BytesIO()
    imgs = list(
        reversed(
            [frame.copy() for frame in ImageSequence.Iterator(img.open(io.BytesIO(b)))]
        )
    )
    imgs[0].save(
        out,
        format="GIF",
        save_all=True,
        append_images=imgs[1:],
    )
    return out.getvalue()


async def _reverse_gif(url: str) -> bytes:
    async with Session.session.get(url) as resp:
        gif = await resp.read()
    if not _check_gif(gif):
        raise NotAGif("非gif")
    return await to_thread(_reverse, gif)

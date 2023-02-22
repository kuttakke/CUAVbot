from pathlib import Path

from graia.ariadne.entry import (
    Ariadne,
    At,
    ElementMatch,
    Group,
    GroupMessage,
    Image,
    MatchResult,
    Member,
    MessageChain,
    MessageEvent,
    Plain,
    RegexMatch,
    Source,
    Twilight,
)
from graia.ariadne.message.parser.twilight import SpacePolicy
from graia.ariadne.util.interrupt import FunctionWaiter
from graiax.shortcut.saya import decorate, dispatch, listen

from core.control import Controller
from core.depend.blacklist import BlackList
from core.entity import Modules
from utils.tool import to_module_file_name

from .img2anime import TraceMoe

module_name = "图搜番"

module = Modules(
    name=module_name,
    author="Kutake",
    description="图搜番，API源于trace.moe",
    usage="""
    .搜番

    .搜番 <图片>

    <@含图片的消息回复> .搜番

    图片要求较为严格，请尽可能保证画面与色彩的完整
    """,
    file_name=to_module_file_name(Path(__file__)),
)

channel = Controller.module_register(module)

searcher = Twilight(
    [
        ElementMatch(At, optional=True).space(SpacePolicy.PRESERVE),
        RegexMatch(r"[.。!！\s]?搜番\s?").space(SpacePolicy.PRESERVE),
        ElementMatch(Image, optional=True).space(SpacePolicy.PRESERVE) @ "img",
    ]
)


@listen(GroupMessage)
@dispatch(searcher)
@decorate(BlackList.require(module_name))
async def from_image_to_anime(
    app: Ariadne,
    group: Group,
    member: Member,
    img: MatchResult,
    source: Source,
    event: MessageEvent,
    msg: MessageChain,
):
    img_url: str | None = None
    if TraceMoe.is_process:
        await app.send_group_message(group, MessageChain("已有查询操作存在，请先等待几秒再操作吧🥰"))
        return
    if event.quote:
        msg_from_id = await app.get_message_from_id(event.quote.id)
        if msg_from_id.message_chain.has(Image):
            img_url = msg_from_id.message_chain.get_first(Image).url

    if img.matched:
        img_url = img.result.url  # type: ignore
    if img_url:
        await app.send_group_message(group, MessageChain("开始搜索..."), quote=source)
        msg = await TraceMoe.run(img_url)
        await app.send_group_message(group, msg)
        return
    await app.send_group_message(
        group,
        MessageChain(
            [At(member.id), Plain("请在30秒内发送要搜索的图片图片呐~(图片要求较为严格，请尽可能保证画面与色彩的完整！)")]
        ),
    )

    async def waiter(
        waiter_group: Group, waiter_member: Member, waiter_message: MessageChain
    ):
        if all(
            [
                waiter_group.id == group.id,
                waiter_member.id == member.id,
                waiter_message.has(Image),
            ]
        ):
            return waiter_message.get_first(Image).url

    img_url = await FunctionWaiter(waiter, [GroupMessage]).wait(timeout=20)
    if not img_url:
        await app.send_group_message(group, MessageChain("搜番操作超时，已取消"))
        return
    await app.send_group_message(
        group, MessageChain("开始搜索！可能需要10秒左右，请耐心等待哦！"), quote=source
    )
    msg = await TraceMoe.run(img_url)
    await app.send_group_message(group, msg)

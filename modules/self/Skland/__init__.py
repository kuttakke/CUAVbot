from pathlib import Path

import aiohttp
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import (
    FriendMessage,
    GroupMessage,
    MessageChain,
    MessageEvent,
)
from graia.ariadne.message.parser.twilight import MatchResult
from graia.ariadne.util.interrupt import FunctionWaiter
from graiax.shortcut.saya import decorate, dispatch, listen, schedule

from core.control import Controller, Modules
from core.depend.blacklist import BlackList
from core.depend.permission import Permission
from utils.msgtool import make_forward_msg, send_debug, send_forward_msg_with_retry
from utils.tool import to_module_file_name

from .command import Command
from .service import get_all_user, get_user_by_qq
from .skland import skland

module_name = "森空岛助手"

module = Modules(
    name=module_name,
    file_name=to_module_file_name(Path(__file__)),
    author="Kutake",
    description="使用森空岛API进行签到和信息查询",
    usage=".森空岛\n\n.森空岛绑定\n\n.森空岛签到\n\n.森空岛信息\n\n.解绑森空岛",
)
channel = Controller.module_register(module)


_cred_help = [
    "请按照以下方法获得凭据，得到后[!私聊!]使用`.森空岛绑定 [凭据]`来进行绑定，例如\n.森空岛绑定 abcabcabc",
    "凭据非常重要！请保护好！不要在公共群聊内泄露凭据！",
    "提示，森空岛网页版：https://www.skland.com/",
    "方法一\n1. 打开森空岛网页版并登录\n2. 打开网页开发工具并切换到 `控制台` 选项卡\n3. 选择 `储存 -> 本地储存 -> https://www.skland.com`\n4. 右侧面板 `SK_OAUTH_CRED_KEY` 的值就是您的凭据",
    '方法二\n1. 打开森空岛网页版并登录\n2. 打开网页开发工具并切换到 `控制台` 选项卡\n3. 在控制台中输入以下内容并回车：`localStorage.getItem("SK_OAUTH_CRED_KEY");`\n4. 控制台返回的值就是您的凭据',
    '方法三\n1. 打开森空岛网页版并登录\n2. 在游览器地址栏中输入以下内容并回车：`javascript:prompt(undefined, localStorage.getItem("SK_OAUTH_CRED_KEY"));`\n3. 浏览器弹出的对话框内的值就是您的凭据',
]


@listen(GroupMessage, FriendMessage)
@dispatch(Command.BindingPlayer)
@decorate(BlackList.require(module_name))
async def binding_player_with_cerd(
    app: Ariadne, event: MessageEvent, cerd: MatchResult
):
    if not cerd.matched:
        await send_forward_msg_with_retry(
            event, MessageChain(make_forward_msg(_cred_help))
        )
        return
    if isinstance(event, GroupMessage):
        return
    async with aiohttp.ClientSession() as session:
        state = await skland.get_user_info(
            session, str(cerd.result).strip(), event.sender.id
        )
    if state.code != 0:
        await app.send_message(event, MessageChain(f"[森空岛] 绑定出现错误：{state.info}"))
        return
    await app.send_message(event, MessageChain(f"请回复编号：\n{state.info}"))

    async def waiter(
        waiter_event: FriendMessage, waiter_message: MessageChain
    ) -> int | None:
        if (
            waiter_event.sender.id == event.sender.id
            and str(waiter_message).strip().isdigit()
        ):
            return int(str(waiter_message).strip())

    res = await FunctionWaiter(waiter, [GroupMessage, FriendMessage]).wait(timeout=30)
    if not res:
        await app.send_message(event, MessageChain("[森空岛] 绑定操作超时"))
        return
    if res > len(skland.temp_user_info[event.sender.id]) or res <= 0:
        await app.send_message(event, MessageChain("[森空岛] 未找到与该编号匹配的数据"))
        return
    await skland.add_user(str(cerd.result).strip(), qid=event.sender.id, index=res)
    await app.send_message(event, MessageChain("[森空岛] 绑定成功"))


@listen(GroupMessage, FriendMessage)
@dispatch(Command.Sign)
@decorate(BlackList.require(module_name))
async def sign(app: Ariadne, event: MessageEvent):
    for user in await get_user_by_qq(event.sender.id):
        async with aiohttp.ClientSession() as session:
            state = await skland.attendance(session, user)
        if state.code != 0:
            await app.send_message(
                event, MessageChain(f"[森空岛] {user.name}签到出现错误：{state.info}")
            )
            continue
        await app.send_message(
            event, MessageChain(f"[森空岛] {user.name}签到成功\n{state.info}")
        )


@listen(GroupMessage)
@dispatch(Command.SignAll)
@decorate(BlackList.require(module_name),Permission.r_debug())
async def sign_all_c(app: Ariadne, event: MessageEvent):
    for user in await get_all_user():
        async with aiohttp.ClientSession() as session:
            state = await skland.attendance(session, user)
        if state.code != 0:
            await app.send_friend_message(
                user.qid, MessageChain(f"[森空岛] {user.name}签到出现错误：{state.info}")
            )
            await send_debug(f"[森空岛] {user.qid}:{user.name}签到出现错误：{state.info}")
            continue
        await app.send_friend_message(
            user.qid, MessageChain(f"[森空岛] {user.name}签到成功\n{state.info}")
        )

@schedule(Command.TimerSign)
async def sign_all(app: Ariadne):
    for user in await get_all_user():
        async with aiohttp.ClientSession() as session:
            state = await skland.attendance(session, user)
        if state.code != 0:
            await app.send_friend_message(
                user.qid, MessageChain(f"[森空岛] {user.name}签到出现错误：{state.info}")
            )
            await send_debug(f"[森空岛] {user.qid}:{user.name}签到出现错误：{state.info}")
            continue
        await app.send_friend_message(
            user.qid, MessageChain(f"[森空岛] {user.name}签到成功\n{state.info}")
        )

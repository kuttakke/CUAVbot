from pathlib import Path
from typing import Optional

from graia.ariadne.app import Ariadne
from graia.ariadne.event.lifecycle import ApplicationLaunched, ApplicationShutdowned
from graia.ariadne.event.message import FriendMessage, GroupMessage
from graia.ariadne.event.mirai import (
    BotGroupPermissionChangeEvent,
    BotInvitedJoinGroupRequestEvent,
    BotJoinGroupEvent,
    BotLeaveEventActive,
    BotLeaveEventKick,
    MemberJoinEvent,
    NewFriendRequestEvent,
)
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Plain
from graia.ariadne.model import Friend, Group
from graia.ariadne.util.interrupt import FunctionWaiter
from graiax.shortcut.saya import listen

from config import settings
from core.control import Controller
from core.entity import Modules
from utils.msgtool import send_debug
from utils.session import Session
from utils.tool import to_module_file_name

module_name = "Bot管理"

module = Modules(
    name=module_name,
    author="Kutake",
    description="好友与群事件管理",
    file_name=to_module_file_name(Path(__file__)),
)
channel = Controller.module_register(module)


@listen(ApplicationLaunched)
async def launched(app: Ariadne):
    group_list = await app.get_group_list()
    quit_groups = 0
    msg = f"{settings.mirai.bot_name} 当前共加入了 {len(group_list) - quit_groups} 个群"
    await send_debug(MessageChain(msg))


@listen(ApplicationShutdowned)
async def shutdowned():
    await Session.close()
    await send_debug(
        MessageChain(
            f"{settings.mirai.bot_name} 正在关闭",
        ),
    )


@listen(NewFriendRequestEvent)
async def new_friend(app: Ariadne, event: NewFriendRequestEvent):
    """
    收到好友申请
    """

    source_group: Optional[int] = event.source_group
    groupname = "未知"
    if source_group:
        group = await app.get_group(source_group)
        groupname = group.name if group else "未知"

    await send_debug(
        MessageChain(
            Plain(f"收到添加好友事件\nQQ：{event.supplicant}\n昵称：{event.nickname}\n"),
            Plain(f"来自群：{groupname}({source_group})\n")
            if source_group
            else Plain("\n来自好友搜索\n"),
            Plain(event.message) if event.message else Plain("无附加信息"),
            Plain("\n\n是否同意申请？请在10分钟内发送“同意”或“拒绝”，否则自动同意"),
        ),
    )

    async def waiter(waiter_group: Group, waiter_message: MessageChain):
        if waiter_group.id == settings.mirai.debug_group:
            saying = waiter_message.display
            if saying == "同意":
                return True
            elif saying == "拒绝":
                return False
            else:
                await app.send_group_message(
                    waiter_group,
                    MessageChain("请发送同意或拒绝"),
                )

    result = await FunctionWaiter(waiter, [GroupMessage]).wait(timeout=120)
    if result is None:
        await event.accept()
        await send_debug(
            MessageChain(f"由于超时未审核，已自动同意 {event.nickname}({event.supplicant}) 的好友请求"),
        )
        return
    if result:
        await event.accept()
        await send_debug(
            MessageChain(Plain(f"已同意 {event.nickname}({event.supplicant}) 的好友请求")),
        )
        return
    await event.reject("Bot 主人拒绝了你的好友请求")
    await send_debug(
        MessageChain(Plain(f"已拒绝 {event.nickname}({event.supplicant}) 的好友请求")),
    )


@listen(BotInvitedJoinGroupRequestEvent)
async def invited_join_group(app: Ariadne, event: BotInvitedJoinGroupRequestEvent):
    """
    被邀请入群
    """

    await send_debug(
        MessageChain(
            "收到邀请入群事件\n"
            f"邀请者：{event.nickname}({event.supplicant})\n"
            f"群号：{event.source_group}\n"
            f"群名：{event.group_name}\n"
            "\n是否同意申请？请在10分钟内发送“同意”或“拒绝”，否则自动拒绝"
        ),
    )

    async def waiter(waiter_group: Group, waiter_message: MessageChain):
        if waiter_group.id == settings.mirai.debug_group:
            saying = waiter_message.display
            if saying == "同意":
                return True
            elif saying == "拒绝":
                return False
            else:
                await app.send_group_message(
                    waiter_group,
                    MessageChain("请发送同意或拒绝"),
                )

    result = await FunctionWaiter(waiter, [GroupMessage]).wait(timeout=120)
    if result is None:
        await event.reject("由于 Bot 管理员长时间未审核，已自动拒绝")
        await send_debug(
            MessageChain(
                f"由于长时间未审核，已自动拒绝 "
                f"{event.nickname}({event.supplicant}) 邀请进入群 {event.group_name}({event.source_group}) 请求"
            ),
        )
        return
    if result:
        await event.accept()
        await send_debug(
            MessageChain(
                f"已同意 {event.nickname}({event.supplicant}) 邀请进入群 {event.group_name}({event.source_group}) 请求"
            ),
        )
        return
    await event.reject("Bot 主人拒绝加入该群")
    await send_debug(
        MessageChain(
            f"已拒绝 {event.nickname}({event.supplicant}) 邀请进入群 {event.group_name}({event.source_group}) 请求"
        ),
    )


@listen(BotJoinGroupEvent)
async def join_group(app: Ariadne, event: BotJoinGroupEvent):
    """
    收到入群事件
    """
    member_num: int = len(await app.get_member_list(event.group))
    await send_debug(
        MessageChain(
            f"收到 Bot 入群事件\n群号：{event.group.id}\n群名：{event.group.name}\n群人数：{member_num}"
        ),
    )
    await app.send_group_message(
        event.group,
        MessageChain(
            f"我是 {settings.mirai.master_name} 的机器人 {settings.mirai.bot_name}\n"
            f"如果有需要可以联系主人QQ『{settings.mirai.master}』\n"
            "直接拉进其他群需要经过主人同意才会入群噢\n"
            "发送 .menu 或 .菜单 可以查看功能列表，群管理员可以开启或禁用功能\n"
        ),
    )


@listen(BotLeaveEventKick)
async def kick_group(event: BotLeaveEventKick):
    """
    被踢出群
    """
    await send_debug(
        MessageChain(f"收到被踢出群聊事件\n群号：{event.group.id}\n群名：{event.group.name}\n"),
    )


@listen(BotLeaveEventActive)
async def leave_group(event: BotLeaveEventActive):
    """
    主动退群
    """
    await send_debug(
        MessageChain(f"收到主动退出群聊事件\n群号：{event.group.id}\n群名：{event.group.name}\n"),
    )


@listen(BotGroupPermissionChangeEvent)
async def permission_change(event: BotGroupPermissionChangeEvent):
    """
    群内权限变动
    """
    await send_debug(
        MessageChain(
            f"收到权限变动事件\n群号：{event.group.id}\n群名：{event.group.name}\n权限变更为：{event.current}"
        ),
    )


@listen(FriendMessage)
async def resend_friend_msg_to_group(app: Ariadne, friend: Friend, msg: MessageChain):
    if "pix登录" in msg.display:
        return
    info = f"收到好友:{friend.nickname}@{friend.id}的消息:\n"
    await send_debug(MessageChain(info).extend(msg.as_sendable()))


@listen(MemberJoinEvent)
async def member_welcome(app: Ariadne, event: MemberJoinEvent, group: Group):
    await app.send_group_message(
        group, MessageChain([Plain("欢迎"), At(event.member), Plain("的加入🥰😍")])
    )

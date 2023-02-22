from pathlib import Path

from graia.ariadne.app import Ariadne, Friend, Group, Member
from graia.ariadne.event.lifecycle import ApplicationLaunched
from graia.ariadne.event.message import FriendMessage, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.parser.twilight import MatchResult
from graiax.shortcut.saya import (
    decorate,
    dispatch,
    every_custom_hours,
    listen,
    schedule,
)
from loguru import logger

from core.control import Controller, Modules
from utils.tool import to_module_file_name

from .command import Command
from .controller import Controller as ctrl

module_name = "原神助手"

module = Modules(
    name=module_name,
    file_name=to_module_file_name(Path(__file__)),
    author="Kutake",
    description="目前仅支持原神树脂提醒",
    usage=(
        "绑定原神 [账号cookies]\n\n"
        "解绑原神 （可选）-u [账号uid]\n\n"
        "更新原神 [账号cookies]\n\n"
        "关闭树脂提醒\n\n"
        "开启树脂提醒\n\n"
        "删除原神 [qq](管理员指令)\n\n"
        "  提示 绑定原神 命令不带 -c 即可查看cookies获取提示"
    ),
)

channle = Controller.module_register(module)

help_url = "https://toscode.gitee.com/ultradream/Genshin-Tools#%E8%8E%B7%E5%8F%96%E7%B1%B3%E6%B8%B8%E7%A4%BEcookie"


@listen(FriendMessage)
@dispatch(Command.AddUser)
async def add_user(app: Ariadne, friend: Friend, cookies: MatchResult):
    if not cookies.matched:
        await app.send_friend_message(friend, MessageChain("cookies获取方法：\n" + help_url))
        return
    if "account_id" not in cookies.result.display:  # type: ignore
        return
    await ctrl.create_user(friend.id, cookies.result.display)  # type: ignore


@listen(FriendMessage)
@dispatch(Command.UpdateUser)
async def update_user(friend: Friend, cookies: MatchResult):
    if not cookies.matched:
        return
    if "account_id" not in cookies.result.display:  # type: ignore
        return
    await ctrl.update_cookies(friend.id, cookies=cookies.result.display)  # type: ignore


@listen(FriendMessage)
@dispatch(Command.RemoveUser)
async def remove_user(friend: Friend, uid: MatchResult):
    if not uid.matched:
        uid_ = None
    elif uid.result.display.strip().isdecimal():  # type: ignore
        uid_ = int(uid.result.display.strip())  # type: ignore
    else:
        return
    await ctrl.remove_user(friend.id, uid_)


# @channel.use(SchedulerSchema(timer=sign_timer))
# async def run_sign():
#     Controller.reset_signed_uids()
#     await Controller.sign()


@listen(FriendMessage)
@dispatch(Command.DailyNote)
async def get_user_daily_note(friend: Friend):
    await ctrl.get_resin(friend.id)


# @channel.use(
#     ListenerSchema(
#         listening_events=[GroupMessage],
#         inline_dispatchers=[sign_cmd],
#         decorators=[ControlModel.root()],
#     )
# )
# async def run_sign_by_manual(app: Ariadne, group: Group):
#     await app.send_group_message(group, MessageChain("开始手动签到原神"))
#     await ctrl.sign()


@listen(FriendMessage)
@dispatch(Command.SwitchDailyNote)
async def switch_user_daily_note_reminder(friend: Friend, cmd: MatchResult):
    function = (
        ctrl.disable_resin_remind
        if "关闭" in cmd.result.display  # type: ignore
        else ctrl.enable_resin_remind
    )
    await function(friend.id)


# @channel.use(
#     ListenerSchema(
#         listening_events=[FriendMessage], inline_dispatchers=[switch_daily_sign_cmd]
#     )
# )
# async def switch_user_daily_sign_reminder(friend: Friend, cmd: MatchResult):
#     function = (
#         ctrl.disable_auto_sign
#         if "关闭" in cmd.result.display
#         else ctrl.enable_auto_sign
#     )
#     await function(friend.id)


# @channel.use(
#     ListenerSchema(
#         listening_events=[GroupMessage],
#         inline_dispatchers=[switch_global_sign_cmd],
#         decorators=[ControlModel.root()],
#     )
# )
# async def switch_global_sign_reminder(cmd: MatchResult):
#     function = (
#         ctrl.disable_global_sign
#         if "关闭" in cmd.result.display
#         else ctrl.enable_global_sign
#     )
#     await function()


@schedule(every_custom_hours(Command.TimeResetResinEveryHour))
async def reset_resin_reminder():
    await ctrl.reset_reminder()


@listen(ApplicationLaunched)
async def init_user_sign_handler():
    logger.info("start check_user_reminder")
    await ctrl.resin_reminder(is_init=True)


@listen(GroupMessage)
@dispatch(Command.DailyNote)
async def get_user_daily_note_group(group: Group, member: Member):
    await ctrl.get_resin_by_group(group.id, member.id)


@listen(GroupMessage)
@dispatch(Command.DeleteUser)
async def delete_user_by_manual(app: Ariadne, group: Group, id: MatchResult):
    try:
        id_ = int(id.result.display)  # type: ignore
    except ValueError:
        await app.send_group_message(group, MessageChain("请输入正确的id"))
        return
    await ctrl.remove_user_by_admin(id_)

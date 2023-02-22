from pathlib import Path

from graia.ariadne.entry import (
    ApplicationLaunch,
    Ariadne,
    Friend,
    FriendMessage,
    Group,
    GroupMessage,
    MatchResult,
    MessageChain,
    MessageEvent,
)
from graia.ariadne.util.interrupt import FunctionWaiter
from graiax.shortcut.saya import (
    decorate,
    dispatch,
    every_custom_minutes,
    listen,
    schedule,
)

from config import settings
from core.control import Controller
from core.depend.permission import Permission
from core.entity import Modules
from utils.msgtool import send_debug
from utils.tool import to_module_file_name

from .command import Command
from .User import User, UserHandler

module_name = "Pixiv订阅更新"

module = Modules(
    name=module_name,
    author="Kutake",
    description="登录自己的pixiv账号，间隔固定时间检测是否存在订阅更新\n存在则发送至账号拥有者，可自定义屏蔽tag, 可翻页\n仅限好友",
    usage="限制型功能，不建议展示",
    file_name=to_module_file_name(Path(__file__)),
)

channel = Controller.module_register(module)


@listen(FriendMessage)
async def send_update_by_user(friend: Friend):
    await UserHandler.update(friend.id)


@listen(FriendMessage)
@dispatch(Command.Login)
async def create_user(
    app: Ariadne,
    friend: Friend,
    user: MatchResult,
    password: MatchResult,
    token: MatchResult,
):
    if not any([all([user.matched, password.matched]), token.matched]):
        await app.send_friend_message(friend, MessageChain("缺少重要参数！"))
        return
    if UserHandler.get_user(friend.id):
        await app.send_friend_message(friend, MessageChain("您的账号已存在哦"))
        return
    if token.matched:
        refresh_token = token.result.display  # type: ignore
        res = await User.create_by_token(friend.id, refresh_token)
    if user.matched:
        await app.send_friend_message(friend, MessageChain("已不支持用户名密码登录"))
        # name = user.result.display  # type: ignore
        # pass_ = password.result.display  # type: ignore
        # res = await User.create_by_password(friend.id, name, pass_)
    if isinstance(res, list):  # type: ignore
        await app.send_friend_message(friend, MessageChain(res))
        return
    UserHandler.add_user(res)  # type: ignore
    await app.send_group_message(
        settings.mirai.debug_group,
        MessageChain(f"{friend.nickname}@{friend.id}创建pix模组用户成功"),
    )
    await app.send_friend_message(
        friend, MessageChain(f"您的@{friend.id}创建pix模组用户成功，今后将受到pix的订阅更新")
    )
    await app.send_friend_message(
        friend,
        MessageChain("bot非公有云部署，数据仅在本地保存，若您对隐私有要求，您有权要求bot删除储存的任何敏感数据（不包括非敏感内容）"),
    )


@listen(FriendMessage)
@dispatch(Command.AddOrRemoveBlockTag)
async def add_or_remove_block_tag(app: Ariadne, friend: Friend, tag: MatchResult):
    if not (user := UserHandler.get_user(friend.id)):
        return
    commend = tag.result.display.split(" ")  # type: ignore
    if len(commend) != 2:
        await app.send_friend_message(friend.id, MessageChain("似乎有奇怪的输入，取消操作"))
        return
    call_ = user.del_block_tag if "解除" in commend[0] else user.add_block_tag

    res = await call_(commend[1])
    if res:
        await app.send_friend_message(friend.id, MessageChain("操作成功"))
    else:
        await app.send_friend_message(friend.id, MessageChain("操作失败，请检查此tag的状态"))


@listen(FriendMessage)
@dispatch(Command.ActivateTrigger)
async def active_or_deactivate_block_tag(
    app: Ariadne, friend: Friend, trigger: MatchResult
):
    commend = trigger.result.display  # type: ignore
    if user := UserHandler.get_user(friend.id):
        call_ = user.deactivate if "关闭" in commend else user.activate
        await call_()
        await app.send_friend_message(friend, MessageChain("操作成功"))


@listen(GroupMessage)
@dispatch(Command.GlobalActivateTrigger)
@decorate(Permission.r_debug())
async def global_active_or_deactivate_block_tag(
    app: Ariadne, group: Group, trigger: MatchResult
):
    commend: str = trigger.result.display  # type: ignore
    user_list = UserHandler.get_all_user()
    for user in user_list:
        if "关闭" in commend:
            await user.deactivate()
        else:
            await user.activate()
    await app.send_group_message(group, MessageChain("操作成功"))


@listen(ApplicationLaunch)
async def init_user():
    await UserHandler.init_user()


@listen(FriendMessage)
@dispatch(Command.DeleteUser)
async def dele_user(app: Ariadne, friend: Friend):
    user = UserHandler.get_user(friend.id)
    if user:
        if UserHandler.is_updating:
            await app.send_friend_message(friend, MessageChain("全局订阅更新中，请等待更新完成"))
            return

        await app.send_friend_message(
            friend, MessageChain("即将在本bot上删除您的pixiv账号， 请输入 yes|no 进行确认")
        )

        async def waiter(waiter_friend: Friend, waiter_message: MessageChain):
            if all(
                [
                    waiter_friend.id == friend.id,
                    waiter_message.display.lower() in ["yes", "no"],
                ]
            ):
                return waiter_message.display.lower()

        commend = await FunctionWaiter(waiter, [FriendMessage]).wait(timeout=30)
        if "yes" == commend:
            await user.destroy()
            UserHandler.remove_user(user.qq_id)
        else:
            await app.send_friend_message(friend, MessageChain("已取消"))


@listen(FriendMessage, GroupMessage)
@dispatch(Command.Status)
async def account_status(app: Ariadne, event: MessageEvent):
    if user := UserHandler.get_user(event.sender.id):
        await app.send_message(event, MessageChain(await user.status()))


@listen(FriendMessage)
@dispatch(Command.Nsfw)
async def nsfw_switch(app: Ariadne, friend: Friend, nsfw: MatchResult):
    if user := UserHandler.get_user(friend.id):
        if "开启" in nsfw.result.display:  # type: ignore
            res = await user.nsfw_switch(True)
            if res:
                await app.send_friend_message(friend, MessageChain("H是可以的！！😍"))
                return
            await app.send_friend_message(friend, MessageChain("已经是启动状态哦🥰"))
        else:
            res = await user.nsfw_switch(False)
            if res:
                await app.send_friend_message(friend, MessageChain("H是不可以的~😉"))
                return
            await app.send_friend_message(friend, MessageChain("已经是关闭状态哦🥰"))


@listen(GroupMessage)
@dispatch(Command.PushUpdate)
@decorate(Permission.r_debug())
async def push_update_event(app: Ariadne, group: Group):
    await app.send_group_message(group, MessageChain("[AutoPix]开始尝试手动更新"))
    await UserHandler.update()
    await app.send_group_message(group, MessageChain("[AutoPix]手动更新完成"))


@listen(GroupMessage)
@dispatch(Command.AllUserStatus)
@decorate(Permission.r_debug())
async def get_all_user_status(app: Ariadne, group: Group):
    if user_list := UserHandler.get_all_user():
        for i in user_list:
            status = await i.status()
            await app.send_group_message(
                group, MessageChain(status.replace("您", f"@{i.qq_id}"))
            )
    else:
        await app.send_group_message(group, MessageChain("无用户"))
    out = UserHandler.get_update_status()
    task_status = UserHandler.is_updating
    await app.send_group_message(
        group, MessageChain(f"{out}\n更新任务状态：{'已取消' if task_status else '运行中'}")
    )


@schedule(Command.TimeStatus)
async def timer_status():
    await send_debug(UserHandler.get_update_status())
    UserHandler.status_clear()


@schedule(every_custom_minutes(Command.TimeUpdateEveryMinutes))
async def timer_update():
    await UserHandler.update()

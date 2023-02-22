import os
import sys
from pathlib import Path

from graia.ariadne.entry import (
    ApplicationLaunch,
    Ariadne,
    FriendMessage,
    Group,
    GroupMessage,
    Image,
    Member,
    MessageChain,
    Saya,
)
from graia.ariadne.event.message import MessageEvent
from graia.ariadne.message.parser.twilight import MatchResult
from graia.ariadne.util.interrupt import FunctionWaiter
from graiax.shortcut.saya import decorate, dispatch, listen

from config import settings
from core.control import Controller
from core.depend.permission import Permission
from core.entity import Modules
from utils.t2i import template2img
from utils.tool import random_banner, to_module_file_name

from .command import Command

module_name = "模组管理"

module = Modules(
    name=module_name,
    author="Kutake,SAGIRI-kawaii",
    description="管理员使用的模组管理",
    usage="""
黑名单控制：

- 在本群禁用模块 `.ban <群组名或ID>`

- 在本群启用模块 `.unban <群组名或ID>`

- 禁止某位群员使用模块 `.ban <群组名或ID> <At群成员>`

- 允许某位群员使用模块 `.unban <群组名或ID> <At群成员>`

模块控制：

- 安装模块 `.install <模块名>`

- 卸载模块 `.uninstall <模块名或ID>`

- 重启模块 `.reload <模块名或ID>`

帮助：

- 列出所有模块 `.菜单` 或 `.menu`

- 模块帮助 `.help <模块名或ID>` 或 `.帮助 <模块名或ID>` 或 `.用法 <模块名或ID>`

bot重启：`.restart`""",
    file_name=to_module_file_name(Path(__file__)),
)

channel = Controller.module_register(module)
saya = Saya.current()


@listen(GroupMessage)
@dispatch(Command.BanUnban)
@decorate(Permission.required(notice=True))
async def ban_unban_group(
    app: Ariadne,
    group: Group,
    cmd: MatchResult,
    module: MatchResult,
    at: MatchResult,
):
    cmd_str: str = cmd.result.display.strip()  # type: ignore
    module_name: str = module.result.display.strip()  # type: ignore
    at_id: int | None = at.result.target if at.matched else None  # type: ignore
    if module_name.isdigit():
        if (name := Controller.get_module_name_by_index(int(module_name))) is None:
            await app.send_message(group, MessageChain("模块ID不存在"))
            return
        module_name = name
    if "unban" in cmd_str:
        if at_id:
            await Controller.unban_member(module_name, group.id, at_id)
            await app.send_message(group, MessageChain(f"已允许{at_id}使用{module_name}"))
        else:
            await Controller.unban_group(module_name, group.id)
            await app.send_message(group, MessageChain(f"已在本群启用{module_name}"))
    elif at_id:
        await Controller.ban_member(module_name, group.id, at_id)
        await app.send_message(group, MessageChain(f"已禁止{at_id}使用{module_name}"))
    else:
        await Controller.ban_group(module_name, group.id)
        await app.send_message(group, MessageChain(f"已在本群禁用{module_name}"))


@listen(ApplicationLaunch)
async def modules_status(app: Ariadne):
    await app.send_group_message(
        settings.mirai.debug_group, MessageChain(f"bot启动成功，共{len(saya.channels)}个模块被加载")
    )


@listen(GroupMessage)
@dispatch(Command.InstallUninstall)
@decorate(Permission.r_debug())
async def install_uninstall_module(
    app: Ariadne, group: Group, cmd: MatchResult, module: MatchResult
):
    cmd_str: str = cmd.result.display.strip()  # type: ignore
    module_name: str = module.result.display.strip()  # type: ignore
    if module_name.isdigit():
        if (name := Controller.get_module_name_by_index(int(module_name))) is None:
            await app.send_message(group, MessageChain("模块ID不存在"))
            return
        module_name = name
    if not (module_path := await Controller.get_file_path_by_name(module_name)):
        await app.send_message(group, MessageChain(f"模块{module_name}不存在"))
        return
    if "uninstall" in cmd_str:
        await app.send_message(
            group, MessageChain(Controller.uninstall_modules(module_path))
        )
        return
    await app.send_message(group, MessageChain(Controller.install_modules(module_path)))


@listen(GroupMessage)
@dispatch(Command.Reload)
@decorate(Permission.r_debug())
async def reload_module(app: Ariadne, group: Group, module: MatchResult):
    module_name: str = module.result.display.strip()  # type: ignore
    if module_name.isdigit():
        if (name := Controller.get_module_name_by_index(int(module_name))) is None:
            await app.send_message(group, MessageChain("模块ID不存在"))
            return
        module_name = name
    if not (module_path := await Controller.get_file_path_by_name(module_name)):
        await app.send_message(group, MessageChain(f"模块{module_name}不存在"))
        return
    await app.send_message(group, MessageChain(Controller.reload_modules(module_path)))


@listen(GroupMessage)
@dispatch(Command.Restart)
@decorate(Permission.r_debug())
async def restart(app: Ariadne, group: Group, member: Member):
    await app.send_message(group, MessageChain("请输入yes确认重启"))

    async def waiter(waiter_group: Group, waiter_member: Member, message: MessageChain):
        if (
            waiter_group.id == group.id
            and waiter_member.id == member.id
            and message.display == "yes"
        ):
            return MessageChain("正在重启...")

    res = await FunctionWaiter(waiter, [GroupMessage]).wait(
        timeout=15, default=MessageChain("重启已取消")
    )
    await app.send_message(group, res)
    # NOTE - 可能会出现不可预知的错误
    python = sys.executable
    os.execl(python, python, *sys.argv)


# test template image

TEMPLATE_PATH = Path(__file__).parent / "templates"


@listen(GroupMessage)
@dispatch(Command.Menu)
async def menu_(app: Ariadne, group: Group):
    block_list = [i.module for i in await Controller.get_block_list(group.id)]
    modules = [
        (i + 1, m.meta["name"], m.meta["name"] not in block_list, False)
        for i, m in enumerate(saya.channels.values())
    ]
    if len(modules) % 3:
        modules.extend([(None, None, None, None) for _ in range(3 - len(modules) % 3)])  # type: ignore
    img = await template2img(
        TEMPLATE_PATH / "plugins.html",
        {
            "settings": modules,
            "banner": await random_banner(),
            "title": "CUAV-BOT帮助菜单",
            "subtitle": "CREATED BY CUAV-BOT",
        },
    )
    await app.send_message(group, MessageChain([Image(data_bytes=img)]))


@listen(GroupMessage, FriendMessage)
@dispatch(Command.Help)
async def help_(app: Ariadne, event: MessageEvent, module: MatchResult):
    module_name: str = module.result.display.strip()  # type: ignore
    if module_name.isdigit():
        if (name := Controller.get_module_name_by_index(int(module_name))) is None:
            await app.send_message(event, MessageChain("模块ID不存在"))
            return
        module_name = name
    module_instance: Modules = await Controller.get_module_by_name(module_name)  # type: ignore
    img = await template2img(
        (TEMPLATE_PATH / "plugin_detail.html").read_text(encoding="utf-8"),
        {
            "display_name": module_instance.name,
            "module": module_instance.file_name,
            "banner": await random_banner(),
            "authors": module_instance.author.split(",")
            if module_instance.author
            else ["暂无"],
            "description": module_instance.description or "暂无",
            "usage": module_instance.usage or "暂无",
            "example": module_instance.example or "暂无",
            "maintaining": await Controller.is_block(module_name, event.sender.group.id)
            if isinstance(event, GroupMessage)
            else True,
        },
    )
    await app.send_message(event, MessageChain(Image(data_bytes=img)))

from pathlib import Path

from graia.ariadne.app import Ariadne
from graia.ariadne.event.lifecycle import ApplicationLaunch
from graia.ariadne.event.message import Group, GroupMessage, Member
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.parser.twilight import MatchResult
from graiax.shortcut.saya import crontabify, decorate, dispatch, listen, schedule

from core.control import Controller, Modules
from core.depend.blacklist import BlackList
from core.depend.permission import Permission
from utils.msgtool import make_forward_msg
from utils.tool import to_module_file_name

from .chatbot import chat
from .command import Command

module_name = "ChatGPT对话"

module = Modules(
    name=module_name,
    file_name=to_module_file_name(Path(__file__)),
    author="Kutake",
    description="使用ChatGPT进行对话",
    usage=".chat .ai .chatgpt .openai 对话\n\n.角色列表 \n\n.设置角色 角色ID",
    example=".chat 你好\n\n.角色列表\n\n.设置角色 1",
)
channel = Controller.module_register(module)


@listen(GroupMessage)
@dispatch(Command.Ask)
@decorate(BlackList.require(module_name))
async def chat_gpt(app: Ariadne, group: Group, member: Member, ask: MatchResult):
    await app.send_message(group, MessageChain("Thinking..."))
    res = await chat.ask(group.id, member.id, str(ask.result).strip())
    await app.send_message(group, MessageChain(res))


@listen(GroupMessage)
@dispatch(Command.RoleList)
@decorate(BlackList.require(module_name))
async def get_role_list(app: Ariadne, group: Group):
    await app.send_message(
        group,
        make_forward_msg(
            [
                "以下是ChatGpt角色列表\n0. 默认",
                "\n".join(
                    [f"{i}. {role}" for i, role in enumerate(chat.EXTRA_PROMPT, 1)]
                ),
            ]
        ),
    )


@listen(GroupMessage)
@dispatch(Command.SetRole)
@decorate(BlackList.require(module_name))
async def set_role(app: Ariadne, group: Group, role: MatchResult):
    if (role_id := str(role.result).strip()).isdigit():
        role_id = int(role_id)
        if role_id in range(len(chat.EXTRA_PROMPT) + 1):
            title = await chat.set_role(group.id, role_id)
            await app.send_message(group, MessageChain(f"设置AI角色为 {title} 成功"))
        else:
            await app.send_message(group, MessageChain("角色不存在"))
    else:
        await app.send_message(group, MessageChain("角色不存在"))


@listen(ApplicationLaunch)
async def init():
    await chat.load_prompt()


@listen(GroupMessage)
@dispatch(Command.Usage)
@decorate(BlackList.require(module_name))
async def get_usage(app: Ariadne, group: Group, member: Member):
    r = await chat.get_usage(group.id, member.id)
    await app.send_message(
        group,
        MessageChain(
            f"本群共消耗 {r[0]}token({0.002 * (r[0] / 1000):.3f}美元)\n"
            f"你共消耗 {r[1]}token({0.002 * (r[1] / 1000):.3f}美元)"
        ),
    )


@listen(GroupMessage)
@dispatch(Command.TotalUsage)
@decorate(Permission.r_debug())
async def get_total_usage(app: Ariadne, group: Group):
    r = await chat.get_total_usage()
    await app.send_message(
        group,
        MessageChain(f"API总共消耗 {r}token({0.002 * (r / 1000):.3f}美元)"),
    )


@listen(GroupMessage)
@dispatch(Command.ResetChat)
@decorate(BlackList.require(module_name))
async def reset_chat(app: Ariadne, group: Group, member: Member):
    await chat.reset_chat(group.id, member.id)
    await app.send_message(group, MessageChain("已重置对话"))


@schedule(crontabify(Command.TimeReset))
async def time_reset():
    await chat.reset_all_chat()

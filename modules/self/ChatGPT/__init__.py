from pathlib import Path

from graia.ariadne.app import Ariadne

# from graia.ariadne.event.lifecycle import ApplicationLaunch
from graia.ariadne.event.message import Group, GroupMessage, Member
from graia.ariadne.message.chain import At, MessageChain, Plain
from graia.ariadne.message.parser.twilight import MatchResult
from graia.ariadne.util.interrupt import FunctionWaiter
from graiax.shortcut.saya import crontabify, decorate, dispatch, listen, schedule

from core.control import Controller, Modules
from core.depend.blacklist import BlackList
from core.depend.permission import Permission
from utils.msgtool import make_forward_msg
from utils.tool import to_module_file_name

from .chatbot import CustomRole, chat
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


# @listen(GroupMessage)
# @dispatch(Command.RoleList)
# @decorate(BlackList.require(module_name))
# async def get_role_list(app: Ariadne, group: Group):
#     await app.send_message(
#         group,
#         make_forward_msg(
#             [
#                 "以下是ChatGpt角色列表\n0. 默认",
#                 "\n".join(
#                     [f"{i}. {role}" for i, role in enumerate(chat.EXTRA_PROMPT, 1)]
#                 ),
#             ]
#         ),
#     )


@listen(GroupMessage)
@dispatch(Command.SetRole)
@decorate(BlackList.require(module_name))
async def set_role(app: Ariadne, group: Group, role: MatchResult):
    if (role_id := str(role.result).strip()).isdigit():
        role_id = int(role_id)
        if role_id == 0 or await chat.is_role_exitst(group.id, role_id):
            title = await chat.set_role(group.id, role_id)
            await app.send_message(group, MessageChain(f"设置AI角色为 {title} 成功"))
        else:
            await app.send_message(group, MessageChain("角色不存在"))
    else:
        await app.send_message(group, MessageChain("角色不存在"))


# @listen(ApplicationLaunch)
# async def init():
#     await chat.load_prompt()


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


@listen(GroupMessage)
@dispatch(Command.AddCustomRole)
@decorate(BlackList.require(module_name))
async def add_role(app: Ariadne, group: Group, member: Member):
    await app.send_group_message(
        group,
        MessageChain([At(member), Plain("开始添加自定义角色，全程可输入 `取消` 来取消操作\n1. 请输入角色名：")]),
    )

    async def waiter(
        waiter_group: Group, waiter_member: Member, waiter_message: MessageChain
    ) -> str | None:
        if waiter_group.id == group.id and waiter_member.id == member.id:
            return str(waiter_message).strip()

    res = await FunctionWaiter(waiter, [GroupMessage]).wait(timeout=30)
    if not res:
        await app.send_group_message(group, MessageChain("添加自定义角色操作超时"))
        return
    if res == "取消":
        await app.send_group_message(group, MessageChain("操作取消~"))
        return
    await app.send_group_message(group, MessageChain(f"角色名为：{res}\n2. 请输入设定信息:"))
    role_name = res
    prompt_list = []
    while True:
        res = await FunctionWaiter(waiter, [GroupMessage]).wait(timeout=60)
        if not res:
            await app.send_group_message(group, MessageChain("添加自定义角色操作超时"))
            return
        if res == "取消":
            await app.send_group_message(group, MessageChain("操作取消~"))
            return
        if res == "结束设定":
            if not prompt_list:
                await app.send_group_message(group, MessageChain("无设定添加，退出添加操作"))
                return
            await app.send_group_message(
                group, MessageChain(f"一共添加 {len(prompt_list)} 条设定，添加结束")
            )
            break
        prompt_list.append(res)
        await app.send_group_message(
            group,
            MessageChain(f"已添加{len(prompt_list)}条设定，您可继续输入添加设定，也可使用 `结束设定` 来结束设定操作"),
        )
    await app.send_group_message(
        group, MessageChain(f"3. 请输入符合{role_name}角色设定的第一条回复\n例(设定为猫娘)：喵~你好主人")
    )
    prompt = chat.WRAP_LABEL.join(prompt_list)
    res = await FunctionWaiter(waiter, [GroupMessage]).wait(timeout=30)
    if not res:
        await app.send_group_message(group, MessageChain("添加自定义角色操作超时"))
        return
    if res == "取消":
        await app.send_group_message(group, MessageChain("操作取消~"))
        return
    default_reply = res
    role = CustomRole(
        group_id=group.id,
        member_id=member.id,
        role_name=role_name,
        role_prompt=prompt,
        default_reply=default_reply,
    )
    role = await chat.add_custom_role(role)
    await app.send_group_message(group, MessageChain(f"🎈添加角色成功，ID编号为：{role.id}"))


@listen(GroupMessage)
@dispatch(Command.ShowCustomRole)
@decorate(BlackList.require(module_name))
async def show_role(app: Ariadne, group: Group, member: Member):
    roles = await chat.get_custom_role(group.id)
    info = [
        f"ID: {role.id}\n角色名: {role.role_name}\nprompt:\n\n{role.role_prompt}"
        for role in roles
    ]
    msg = MessageChain(make_forward_msg(info)) if info else MessageChain("本群暂无自定义角色哦")
    await app.send_group_message(group, msg)


@listen(GroupMessage)
@dispatch(Command.RemoveCustomRole)
@decorate(BlackList.require(module_name))
async def remove_role(app: Ariadne, group: Group, role: MatchResult):
    if not str(role.result).isdigit():
        await app.send_group_message(group, MessageChain("需要回复数字ID才可以删除角色哦"))
        return
    cr = await chat.remove_custom_role(group.id, int(str(role.result)))
    if cr:
        await app.send_group_message(
            group, MessageChain(f"成功删除ID为{cr.id}的[{cr.role_name}]角色")
        )
    else:
        await app.send_group_message(group, MessageChain("删除失败，没有找到该自定义角色"))


@schedule(crontabify(Command.TimeReset))
async def time_reset():
    await chat.reset_all_chat()

from datetime import datetime, timedelta
from pathlib import Path

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, GroupMessage, Member, MessageChain
from graia.ariadne.message.element import Source
from graia.ariadne.message.parser.base import MatchRegex
from graiax.shortcut.saya import decorate, listen

from core.control import Controller, Modules
from core.depend.blacklist import BlackList
from utils.tool import to_module_file_name

from .maker import WordCloudMaker

module_name = "聊天记录词云"

module = Modules(
    name=module_name,
    file_name=to_module_file_name(Path(__file__)),
    author="Kutake",
    description="在给定日期内使用聊天记录生成词云",
    usage=".今日词云\n\n.本周词云\n\n.本月词云\n\n.本年词云\n\n.月度词云\n\n.年度词云",
)
channel = Controller.module_register(module)


@listen(GroupMessage)
@decorate(MatchRegex(r"^[.。！!]?(今日|本周|本月|本年|月度|年度)词云$"))
@decorate(BlackList.require(module_name))
async def word_cloud(
    message: MessageChain, group: Group, member: Member, source: Source
):
    if "今日" in message.display:
        time = datetime.now() - timedelta(hours=24)
    elif "本周" in message.display:
        time = datetime.now() - timedelta(days=7)
    elif "本月" in message.display or "月度" in message.display:
        time = datetime.now() - timedelta(days=30)
    elif "本年" in message.display or "年度" in message.display:
        time = datetime.now() - timedelta(days=365)
    else:
        return
    await WordCloudMaker.loop_make(group.id, member.id, source, time)

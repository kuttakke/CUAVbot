"""
from:
https://github.com/I-love-study/A_Simple_QQ_Bot/blob/Ariadne_Version/plugins/entertain/nbnhhsh.py
能不能好好说话
"""

from pathlib import Path

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.parser.twilight import (
    MatchResult,
    RegexMatch,
    SpacePolicy,
    Twilight,
    WildcardMatch,
)
from graia.ariadne.model import Group
from graiax.shortcut.saya import decorate, dispatch, listen

from core.control import Controller, Modules
from core.depend.blacklist import BlackList
from utils.session import Session
from utils.tool import to_module_file_name

module_name = "能不能好好说话"
module = Modules(
    name=module_name,
    file_name=to_module_file_name(Path(__file__)),
    author="I-love-study",
    description="使用API查找字母缩写可能的全程",
    usage=".nbnhhsh [keyword] | .能不能好好说话 [keyword]",
    example=".nbnhhsh yyds | .能不能好好说话 yyds",
)
channel = Controller.module_register(module)

Match = Twilight(
    [
        RegexMatch(r"[.。!！](nbnhhsh|能不能好好说话)").space(SpacePolicy.FORCE),
        WildcardMatch(greed=False) @ "para",
    ]
)


@listen(GroupMessage)
@dispatch(Match)
@decorate(BlackList.require(module_name))
async def nbnhhsh(app: Ariadne, group: Group, para: MatchResult):
    if not para.matched:
        msg = "能不能好好说话"
    else:
        js = {"text": para.result.display.strip()}  # type: ignore
        url = "https://lab.magiconch.com/api/nbnhhsh/guess"
        try:
            ret: dict = (
                await Session.request("POST", url, response_type="json", json=js)
            )[0]
        except Exception as e:
            await app.send_group_message(group, MessageChain(f"[能不能好好说话]解析失败:{e}"))
            return
        if (w := ret.get("trans")) and len(w):
            msg = f"缩写{ret['name']}的全称:\n" + "\n".join(w)
        elif (w := ret.get("inputting")) and len(w):
            msg = f"缩写{ret['name']}的全称:\n" + "\n".join(w)
        else:
            msg = f"没找到{ret['name']}的全称"

    await app.send_group_message(group, MessageChain(msg))

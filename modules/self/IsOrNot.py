from pathlib import Path
from random import randint

from graia.ariadne.app import Ariadne, Group, GroupMessage, MessageChain
from graia.ariadne.message.element import Source
from graia.ariadne.message.parser.twilight import MatchResult, RegexMatch, Twilight
from graiax.shortcut.saya import decorate, dispatch, listen

from core.control import Controller, Modules
from core.depend.blacklist import BlackList
from utils.tool import to_module_file_name

module_name = "是或不是"
module = Modules(
    name=module_name,
    description="触发条件:\n" "XX是不是XXXX\n" "是不是XXXX",
    file_name=to_module_file_name(Path(__file__)),
    author="Kutake",
)
channel = Controller.module_register(module)

CMD = Twilight([RegexMatch(r"\S*是不是\S*") @ "word"])


@listen(GroupMessage)
@dispatch(CMD)
@decorate(BlackList.require(module_name))
async def _(app: Ariadne, group: Group, word: MatchResult, source: Source):
    current: str = word.result.display  # type: ignore
    if current == "是不是":
        return
    await app.send_group_message(
        group,
        MessageChain(f"{'是' if randint(0, 1) else '不是'}"),
        quote=source,
    )

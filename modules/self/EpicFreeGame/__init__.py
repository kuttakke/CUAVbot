import re
from pathlib import Path

from graia.ariadne.app import Ariadne, Group
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.parser.twilight import RegexMatch, Twilight
from graiax.shortcut.saya import decorate, dispatch, listen, schedule

from core.control import Controller, Modules
from core.depend.blacklist import BlackList
from utils.msgtool import send_message_by_black_list
from utils.tool import to_module_file_name

from .service import get_msg

module_name = "Epic周免"
module = Modules(
    name=module_name,
    file_name=to_module_file_name(Path(__file__)),
    author="Kutake",
    description="Epic商城每周免费游戏订阅",
)
channel = Controller.module_register(module)


Now = Twilight([RegexMatch(r"^本周epic$").flags(re.RegexFlag(re.IGNORECASE))])


@schedule("30 20 * * 4")
@schedule("30 20 * * 2")
@schedule("30 20 * * 6")
async def free_epic():
    await send_message_by_black_list(module_name, await get_msg())


@listen(GroupMessage)
@dispatch(Now)
@decorate(BlackList.require(module_name))
async def last_free_game(app: Ariadne, group: Group):
    await app.send_group_message(group, await get_msg())

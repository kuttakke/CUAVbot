from pathlib import Path

from graia.ariadne.entry import (
    Ariadne,
    FriendMessage,
    GroupMessage,
    Image,
    MessageChain,
)
from graia.ariadne.event.message import MessageEvent
from graia.ariadne.message.parser.twilight import RegexMatch, Twilight
from graiax.shortcut.saya import dispatch, listen

from core.control import Controller
from core.entity import Modules
from utils.tool import to_module_file_name

from .status import StatusInfo

module_name = "Bot状态信息"

module = Modules(
    name=module_name,
    author="Kutake",
    description="bot各种系统信息",
    usage="`.Status` 或 `.状态`",
    file_name=to_module_file_name(Path(__file__)),
)

status_cmd = Twilight([RegexMatch(r"[.。！!](Status|状态)")])

channel = Controller.module_register(module)


@listen(GroupMessage, FriendMessage)
@dispatch(status_cmd)
async def bot_status(app: Ariadne, event: MessageEvent):
    await app.send_message(
        event, MessageChain([Image(data_bytes=await StatusInfo.info_img_bytes())])
    )

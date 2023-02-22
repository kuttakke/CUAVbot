from io import BytesIO
from pathlib import Path

from graia.ariadne.entry import (
    Ariadne,
    Group,
    GroupMessage,
    Image,
    MessageChain,
    Plain,
    RegexMatch,
    Twilight,
)
from graia.scheduler.timers import crontabify
from graiax.shortcut.saya import decorate, dispatch, listen, schedule
from loguru import logger

from core.control import Controller, Modules
from core.depend.blacklist import BlackList
from utils.func_retry import aretry
from utils.msgtool import send_debug, send_message_by_black_list
from utils.session import Session
from utils.tool import to_module_file_name

module_name = "摸鱼日报"
module = Modules(
    name=module_name,
    description="摸鱼Time！每日九点准时发送！",
    file_name=to_module_file_name(Path(__file__)),
    author="Kutake",
)
channel = Controller.module_register(module)

CMD = Twilight([RegexMatch(r"[.。！!]摸鱼日报")])

API: str = "https://api.vvhan.com/api/moyu"


@aretry()
async def get_moyu() -> bytes:
    async with Session.session.get(API) as resp:
        return BytesIO(await resp.read()).getvalue()


@listen(GroupMessage)
@dispatch(CMD)
@decorate(BlackList.require(module_name))
async def moyu(app: Ariadne, group: Group):
    try:
        await app.send_group_message(
            group, MessageChain(Image(data_bytes=await get_moyu()))
        )
    except Exception as e:
        logger.error(e)
        await app.send_group_message(group, Plain(f"摸鱼日报发送失败！:\n{e}"))


@schedule(crontabify("0 9 * * *"))
async def moyu_schedule():
    try:
        await send_message_by_black_list(
            module_name, MessageChain(Image(data_bytes=await get_moyu()))
        )
    except Exception as e:
        logger.error(e)
        await send_debug(f"摸鱼日报发送失败！:\n{e}")

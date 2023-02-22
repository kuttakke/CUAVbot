from pathlib import Path

from graia.ariadne.entry import (
    Ariadne,
    FullMatch,
    Group,
    GroupMessage,
    Image,
    MessageChain,
    Twilight,
)
from graiax.shortcut.saya import decorate, dispatch, listen, schedule
from loguru import logger

from core.control import Controller, Modules
from core.depend.blacklist import BlackList
from utils import aretry
from utils.msgtool import send_debug, send_message_by_black_list
from utils.session import Session
from utils.tool import to_module_file_name

module_name = "每日新闻"

module = Modules(
    name=module_name,
    file_name=to_module_file_name(Path(__file__)),
    author="Kutake",
    description="每天九点半触发,手动获取：'今日新闻'",
)

channel = Controller.module_register(module)


News = Twilight([FullMatch("今日新闻")])
TimeReportNews = "30 9 * * *"
# NewsImageApi = "https://api.vvhan.com/api/60s"
NewsImageApi = "http://118.31.18.68:8080/news/api/news-file/get"


@aretry()
async def get_news_image() -> bytes:
    async with Session.session.get(NewsImageApi) as resp:
        url = (await resp.json())["result"]["data"][0]
    async with Session.session.get(url) as resp:
        return await resp.read()


@schedule(TimeReportNews)
async def auto_send_news():
    try:
        await send_message_by_black_list(
            module_name, MessageChain(Image(data_bytes=await get_news_image()))
        )
    except Exception as e:
        logger.error(e)
        await send_debug(f"{module_name}发送失败！:\n{e}")


@listen(GroupMessage)
@dispatch(News)
@decorate(BlackList.require(module_name))
async def send_news(app: Ariadne, group: Group):
    try:
        await app.send_group_message(
            group, MessageChain(Image(data_bytes=await get_news_image()))
        )
    except Exception as e:
        logger.error(e)
        await app.send_group_message(group, MessageChain(f"今日新闻发送失败！:\n{e}"))

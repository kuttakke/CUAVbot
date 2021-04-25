from graia.saya import Saya, Channel
from graia.application.entry import GraiaMiraiApplication
from typing import Optional
import requests
from graia.application.entry import (
    GroupMessage, MessageChain, Image, Group, Plain
)
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.application.message.parser.kanata import Kanata
from graia.application.message.parser.signature import FullMatch
import aiohttp
from utils import master_id
from graia.scheduler.saya.schema import SchedulerSchema
from graia.scheduler.timers import crontabify, every_custom_hours
from utils import logger

# 插件信息
__name__ = "DailyNews"
__description__ = "#  每日新闻"
__author__ = "KuTaKe"
__usage__ = "每天九点半触发\n\u3000手动获取：'今日新闻'"

_report_news = "30 9 * * *"

saya = Saya.current()
bcc = saya.broadcast
channel = Channel.current()

channel.name(__name__)
channel.description(f"{__description__}\n使用方法：\n\u3000{__usage__}")
channel.author(__author__)


@channel.use(SchedulerSchema(
    timer=crontabify(_report_news)
))
async def auto_send_news(app: GraiaMiraiApplication):
    await news.update()
    if news.is_update:
        group_list = await app.groupList()
        for group in group_list:
            await app.sendGroupMessage(group.id, MessageChain.create([Image.fromUnsafeBytes(news.img_bytes)]))
        await app.sendFriendMessage(master_id, MessageChain.create([Image.fromUnsafeBytes(news.img_bytes)]))


@channel.use(SchedulerSchema(
    timer=every_custom_hours(5)
))
async def check_news_update(app: GraiaMiraiApplication):
    if not news.is_update:
        await news.update()
        if news.is_update:
            out_msg = MessageChain.create([Image.fromUnsafeBytes(news.img_bytes)])
            group_list = await app.groupList()
            for group in group_list:
                await app.sendGroupMessage(group.id, out_msg)
            await app.sendFriendMessage(master_id, out_msg)


@channel.use(ListenerSchema(
    listening_events=[GroupMessage],
    inline_dispatchers=[Kanata([FullMatch("今日新闻")])]
))
async def send_news(app: GraiaMiraiApplication, group: Group):
    if not news.is_update:
        await news.update()
    out_msg = MessageChain.create([Plain("每日新闻每天九点半更新哦~"), Image.fromUnsafeBytes(news.img_bytes)])
    await app.sendGroupMessage(group.id, out_msg)


class DailyNews:
    def __init__(self):
        self.is_update: bool = True
        self.img_name: Optional[str] = None
        self.img_bytes = None
        self.api_url: str = "http://api.soyiji.com//news_jpg"
        self._initialize()

    def _initialize(self):
        res = requests.get(self.api_url).json()
        url: str = res["news_url"]
        self.img_name = url.split("/")[-1]
        self.img_bytes = requests.get(url, headers={"Referer": "safe.soyiji.com"}).content

    async def update(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(url=self.api_url) as res_api:
                data = await res_api.json()
                url = data["news_url"]
                name = url.split("/")[-1]
                logger.info(f"新闻更新情况\n{self.img_name} : {name}")
                if self.img_name == name:
                    self.is_update = False
                    logger.info("新闻更新失败")
                else:
                    async with session.get(url=url, handers={"Referer": "safe.soyiji.com"}) as res_img:
                        self.img_bytes = await res_img.read()
                    self.img_name = name
                    self.is_update = True
                    logger.info("新闻更新成功")


news = DailyNews()

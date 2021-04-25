from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.application.entry import (
    MessageChain, GraiaMiraiApplication, GroupMessage, Group, Image, Plain
)
from graia.application.message.parser.kanata import Kanata
from graia.application.message.parser.signature import FullMatch, RequireParam
from utils import logger
import aiohttp


# 插件信息
__name__ = "Choyen5000"
__description__ = "#  日本综艺风格图片生成"
__author__ = "KuTaKe"
__usage__ = "发送 'cy5 文本一 文本二' 即可"

_commond = ".帮助"


saya = Saya.current()
bcc = saya.broadcast
channel = Channel.current()

channel.name(__name__)
channel.description(f"{__description__}\n使用方法：\n\u3000{__usage__}")
channel.author(__author__)


@channel.use(ListenerSchema(
    listening_events=[GroupMessage],
    inline_dispatchers=[Kanata([FullMatch("cy5"), RequireParam("text")])]
))
async def send_img(app: GraiaMiraiApplication, group: Group, text: MessageChain):
    text_list = text.asDisplay().strip().split()
    logger.info(text_list)
    if len(text_list) == 2:
        logger.info(f"触发cy5:[{text_list[0]},{text_list[1]}]")
        url = f"https://api.dihe.moe/5000choyen/?upper={text_list[0]}&lower={text_list[1]}"
        async with aiohttp.request("GET", url) as res:
            img_bytes = await res.read()
        await app.sendGroupMessage(group.id, MessageChain.create([Image.fromUnsafeBytes(img_bytes)]))
    else:
        await app.sendGroupMessage(group.id, MessageChain.create([Plain("输入参数不合法")]))

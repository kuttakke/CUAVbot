from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from prettytable import PrettyTable
from graia.application.entry import GraiaMiraiApplication
from io import BytesIO
from typing import Union
from graia.application.entry import (
    FriendMessage, GroupMessage, MessageChain, Image as Img, Friend, Group, ApplicationLaunched
)
from graia.application.message.parser.kanata import Kanata
from graia.application.message.parser.signature import FullMatch
from PIL import Image, ImageDraw, ImageFont

# 插件信息
__name__ = "BotHelp"
__description__ = "#  bot帮助"
__author__ = "KuTaKe"
__usage__ = "发送'.帮助'即可"

_commond = ".帮助"


saya = Saya.current()
bcc = saya.broadcast
channel = Channel.current()

channel.name(__name__)
channel.description(f"{__description__}\n使用方法：\n\u3000{__usage__}")
channel.author(__author__)


@channel.use(ListenerSchema(
    listening_events=[FriendMessage],
    inline_dispatchers=[Kanata([FullMatch(_commond)])]
))
async def friend_listener(app: GraiaMiraiApplication, friend: Friend):
    out = table.img_bytes
    await app.sendFriendMessage(friend, MessageChain.create([Img.fromUnsafeBytes(out.getvalue())]))


@channel.use(ListenerSchema(
    listening_events=[GroupMessage],
    inline_dispatchers=[Kanata([FullMatch(_commond)])]
))
async def group_listener(app: GraiaMiraiApplication, group: Group):
    out = table.img_bytes
    await app.sendGroupMessage(group, MessageChain.create([Img.fromUnsafeBytes(out.getvalue())]))


@channel.use(ListenerSchema(
    listening_events=[ApplicationLaunched]
))
async def master_online():
    table.get_img()


class Table:
    def __init__(self):
        self.img_bytes = None

    def get_img(self):
        table = PrettyTable()
        table.field_names = ["模块名", "作者", "说明"]
        table.align["说明"] = "l"
        channels = saya.channels
        for channel_name, channel_object in channels.items():
            table.add_row([channel_object._name, channel_object._author[0], channel_object._description])
        out_img = BytesIO()
        out = TTI.img_handler(table.get_string(), out_img)
        self.img_bytes = out


class TTI:
    _font_path = "./modules/BotHelp/simhei.ttf"

    @classmethod
    def img_handler(cls, text: str, save: Union[str, BytesIO]):
        list_ = text.split('\n')
        str_len = len(list_[0])
        str_line = int(len(list_))
        img = Image.new("RGB", (str_len * 12, str_line * 30), (178, 148, 152))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(cls._font_path, 22, encoding="utf-8")
        draw.text((20, 40), text, font=font, fill=(0, 0, 0))
        if isinstance(save, str):
            img.save(r"{}.png".format(save))
            print("{} save".format(save))
        elif isinstance(save, BytesIO):
            img.save(save, format='PNG')
            return save


table = Table()

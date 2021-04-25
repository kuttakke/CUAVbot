from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.application.entry import (
    MessageChain, GraiaMiraiApplication, FriendMessage, Plain, Friend, Image, GroupMessage, Group
)
from graia.application.message.parser.kanata import Kanata
from graia.application.message.parser.signature import FullMatch, OptionalParam
from .setu import SeTu

# 插件信息
__name__ = "SeTu"
__description__ = "#  涩图相关"
__author__ = "KuTaKe"
__usage__ = "随机 '.涩图'\n\u3000搜索 '.涩图 关键词'"

# lolicon_api_key
_api_key = "你的apikey"
# 图片保存地址
_path = "./pixiv_img"

_setu_commond = ".涩图"


saya = Saya.current()
bcc = saya.broadcast
channel = Channel.current()

channel.name(__name__)
channel.description(f"{__description__}\n使用方法：\n\u3000{__usage__}")
channel.author(__author__)


@channel.use(ListenerSchema(
    listening_events=[FriendMessage],
    inline_dispatchers=[Kanata([FullMatch(_setu_commond), OptionalParam(name="keyword")])]
))
async def friend_setu_handler(app: GraiaMiraiApplication, friend: Friend, keyword: MessageChain):
    if keyword is None:
        keyword_str = ""
    else:
        keyword_str = keyword.asDisplay().strip()
    res = await setu.get_setu_with_keyword(True, keyword_str)
    if res is None:
        await app.sendFriendMessage(friend, MessageChain.create([Plain("没有找到这个tag...")]))
    elif res is False:
        await app.sendFriendMessage(friend, MessageChain.create([Plain("请求好像失败了QAQ")]))
    else:
        pid = "pid:" + res[0]
        out = res[1]
        await app.sendFriendMessage(friend, MessageChain.create([Plain(pid), Image.fromUnsafeBytes(out)]))


@channel.use(ListenerSchema(
    listening_events=[GroupMessage],
    inline_dispatchers=[Kanata([FullMatch(_setu_commond), OptionalParam(name="keyword")])]
))
async def friend_setu_handler(app: GraiaMiraiApplication, group: Group, keyword: MessageChain):
    if keyword is None:
        keyword_str = ""
    else:
        keyword_str = keyword.asDisplay().strip()
    res = await setu.get_setu_with_keyword(False, keyword_str)
    if res is None:
        await app.sendGroupMessage(group, MessageChain.create([Plain("没有找到这个tag...")]))
    elif res is False:
        await app.sendGroupMessage(group, MessageChain.create([Plain("请求好像失败了QAQ")]))
    else:
        pid = "pid:" + res[0]
        out = res[1]
        await app.sendGroupMessage(group, MessageChain.create([Plain(pid), Image.fromUnsafeBytes(out)]))

setu = SeTu(_api_key, _path)

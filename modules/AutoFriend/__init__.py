from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.application.entry import (
    MessageChain, GraiaMiraiApplication, NewFriendRequestEvent, Plain, ApplicationLaunched
)
from graia.application.interrupts import FriendMessageInterrupt
from graia.broadcast.interrupt import InterruptControl
from utils import master_id

__name__ = "AutoFriend"
__description__ = "#  自动处理好友请求"
__author__ = "KuTaKe"
__usage__ = "自动触发"

saya = Saya.current()
bcc = saya.broadcast
channel = Channel.current()
inc = InterruptControl(bcc)

channel.name(__name__)
channel.description(f"{__description__}\n使用方法：\n\u3000{__usage__}")
channel.author(__author__)


@channel.use(ListenerSchema(
    listening_events=[NewFriendRequestEvent]
))
async def friend_request_handler(event: NewFriendRequestEvent, app: GraiaMiraiApplication):
    msg = "收到好友请求：\nQQ：{}\n昵称：{}\n描述消息：{}\n群组：{}\n请输入y/n进行同意或拒绝"
    if event.sourceGroup:
        await app.sendFriendMessage(master_id, MessageChain.create([Plain(
            msg.format(str(event.supplicant), event.nickname, event.message, str(event.sourceGroup))
        )]))
    else:
        await app.sendFriendMessage(master_id, MessageChain.create([Plain(
            msg.format(str(event.supplicant), event.nickname, event.message, "无")
        )]))
    msg = await inc.wait(
        FriendMessageInterrupt(
            master_id, custom_judgement=lambda x: x.messageChain.asDisplay().startswith(
                "y") or x.messageChain.asDisplay().startswith("n")))
    if msg.messageChain.asDisplay().startswith("y"):
        await event.accept()
        await app.sendFriendMessage(master_id, MessageChain.create([Plain("添加成功")]))
        await app.sendFriendMessage(event.supplicant, welcome.welcome_messagechain)
    else:
        await event.reject()
        await app.sendFriendMessage(master_id, MessageChain.create([Plain("已拒绝")]))


@channel.use(ListenerSchema(
    listening_events=[ApplicationLaunched]
))
async def welcome_str_load():
    welcome.read()


class Welcome:
    def __init__(self):
        self.welcome_messagechain = None

    def read(self):
        welcome_path = "./modules/AutoFriend/welcome"
        with open(welcome_path, "r", encoding="utf-8") as f:
            welcome_str = f.read()
        self.welcome_messagechain = MessageChain.create([Plain(welcome_str)])
        return self.welcome_messagechain


welcome = Welcome()

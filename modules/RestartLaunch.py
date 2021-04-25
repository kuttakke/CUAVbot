from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.application.entry import (
    MessageChain, ApplicationLaunched, GraiaMiraiApplication, FriendMessage, Plain, Friend
)
from graia.application.message.parser.kanata import Kanata
from graia.application.message.parser.signature import FullMatch
from utils import master_id
from graia.application.interrupts import FriendMessageInterrupt
from graia.broadcast.interrupt import InterruptControl
from .AutoFriend import Welcome
import sys
import os

# 插件信息
__name__ = "RestartLaunch"
__description__ = "#  bot启动与重启事件"
__author__ = "KuTaKe"
__usage__ = "自动触发"

_restart_commond = ".restart"

saya = Saya.current()
bcc = saya.broadcast
channel = Channel.current()
inc = InterruptControl(bcc)

channel.name(__name__)
channel.description(f"{__description__}\n使用方法：\n\u3000{__usage__}")
channel.author(__author__)


@channel.use(ListenerSchema(
    listening_events=[ApplicationLaunched]
))
async def app_launch(app: GraiaMiraiApplication):
    welcome = Welcome().read()
    await app.sendFriendMessage(master_id, welcome)


@channel.use(ListenerSchema(
    listening_events=[FriendMessage],
    inline_dispatchers=[Kanata([FullMatch(_restart_commond)])]
))
async def app_restart(app: GraiaMiraiApplication, friend: Friend):
    if friend.id == master_id:
        await app.sendFriendMessage(master_id, MessageChain.create([Plain('bot即将重启，请输入yes进行确认')]))
        await inc.wait(
            FriendMessageInterrupt(
                master_id, custom_judgement=lambda x: x.messageChain.asDisplay().startswith("yes")))
        python = sys.executable
        os.execl(python, python, *sys.argv)

from graia.saya import Saya, Channel
from graia.application import GraiaMiraiApplication
from graia.application.entry import MessageChain, Plain, Image
from graia.application.message.elements.internal import Voice
from graia.scheduler.saya.schema import SchedulerSchema
from graia.scheduler.timers import crontabify


# 插件信息
__name__ = "TimeAnnouncement"
__description__ = "#  报时"
__author__ = "KuTaKe"
__usage__ = "定时触发"


saya = Saya.current()
bcc = saya.broadcast
channel = Channel.current()

_report_sleep = "0 0 * * *"
_report_wake_up = "30 7 * * *"
# _report_arknights_jiaomie = "5 12 * * 0"

_go_to_sleep_img_path = "./modules/TimeAnnouncement/快去睡觉.png"
_voice_wake_up_path = "./modules/TimeAnnouncement/wake-the-fxxk-up_.silk"


channel.name(__name__)
channel.description(f"{__description__}\n使用方法：\n\u3000{__usage__}")
channel.author(__author__)


@channel.use(SchedulerSchema(
    timer=crontabify(_report_wake_up)
))
async def wake_up(app: GraiaMiraiApplication):
    group_list = await app.groupList()
    for group in group_list:
        await app.sendGroupMessage(group.id, MessageChain.create([Plain("七点半辣！！")]))
        await app.sendGroupMessage(group.id, MessageChain.create([Voice().fromLocalFile(_voice_wake_up_path)]))


@channel.use(SchedulerSchema(
    timer=crontabify(_report_sleep)
))
async def sleep_time(app: GraiaMiraiApplication):
    group_list = await app.groupList()
    for group in group_list:
        await app.sendGroupMessage(group.id, MessageChain.create([
            Plain("到点了到点了，好孩子该睡觉了！"),
            Image.fromLocalFile(_go_to_sleep_img_path)
        ]))


# @channel.use(SchedulerSchema(
#     timer=every_custom_seconds(10)
# ))
# async def test(app: GraiaMiraiApplication):
#     await app.sendGroupMessage(groud_id, MessageChain.create([
#         Voice().fromLocalFile(_voice_wake_up_path)
#     ]))


# @channel.use(ListenerSchema(
#     listening_events=[FriendMessage],
#     inline_dispatchers=[Kanata([FullMatch(_commond)])]
# ))
# async def test(app: GraiaMiraiApplication):
#     # with open(_voice_test_path, "rb") as f:
#     #     vocie = f.read()
#     # upload_voice = await app.uploadVoice(vocie)
#     await app.sendGroupMessage(groud_id, MessageChain.create([
#         Voice().fromLocalFile(_voice_test_path)
#     ]))

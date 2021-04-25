from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast.schema import ListenerSchema
from graia.scheduler.saya.schema import SchedulerSchema
from graia.application.entry import (
    MessageChain, GraiaMiraiApplication, Plain, FriendMessage, Friend
)
import asyncio
from utils import master_id
from graia.application.message.parser.kanata import Kanata
from graia.application.message.parser.signature import FullMatch, RequireParam
from utils import logger
from .pixiv import Pix
from graia.scheduler.timers import every_custom_hours

__name__ = "AutoPix"
__description__ = "#  自动更新P站订阅并发送"
__author__ = "KuTaKe"
__usage__ = "定时间隔触发"

saya = Saya.current()
bcc = saya.broadcast
channel = Channel.current()

channel.name(__name__)
channel.description(f"{__description__}\n使用方法：\n\u3000{__usage__}")
channel.author(__author__)


# 账号信息
_account_path = "./modules/AutoPix/pixiv_account.json"
# 图片保存路径
_img_save_path = "./pixiv_img"
# 代理（可无）
_proxy = "socks5://192.168.0.60:2089"
# 手动更新命令
_commond = ".pixup"
pix = Pix(_account_path, _img_save_path, proxy=_proxy)


@channel.use(ListenerSchema(
    listening_events=[FriendMessage],
    inline_dispatchers=[Kanata([FullMatch(_commond)])]
))
async def pix_update(app: GraiaMiraiApplication, friend: Friend):
    logger.info("收到手动更新请求，正在处理")
    msg_list = await pix.run(friend.id)
    if not msg_list:
        await app.sendFriendMessage(friend, MessageChain.create([Plain("无更新哟~再等一会吧~~")]))
    elif isinstance(msg_list, list):

        async def send_msg_list(m_list):
            for msg in m_list:
                await app.sendFriendMessage(master_id, MessageChain.create(msg))
                await asyncio.sleep(1)
            await app.sendFriendMessage(master_id, MessageChain.create([Plain("结束")]))

        try:
            await send_msg_list(msg_list)
        except BaseException as e:
            logger.error("发送时出错：")
            logger.error(str(e))
            await app.sendFriendMessage(master_id, MessageChain.create([Plain("发送时出错，具体类型请看日志，等待450s重试")]))
            await asyncio.sleep(450)
            await send_msg_list(msg_list)


@channel.use(SchedulerSchema(
    timer=every_custom_hours(2)
))
async def auto_send_pix_update(app: GraiaMiraiApplication):
    if pix.auto:
        account_list = pix.get_account_list()
        for account in account_list:
            try:
                msg_list = await pix.run(account)
            except BaseException as er:
                logger.error("请求或者下载时出错:")
                logger.error(er)
                await app.sendFriendMessage(account, MessageChain.create([Plain("请求或者下载时出错")]))
            else:
                if not msg_list:
                    pass
                elif isinstance(msg_list, list):

                    async def send_msg_list(m_list):
                        for msg in m_list:
                            await app.sendFriendMessage(account, MessageChain.create(msg))
                            await asyncio.sleep(5)
                        await app.sendFriendMessage(account, MessageChain.create([Plain("结束")]))

                    try:
                        await send_msg_list(msg_list)
                    except BaseException as e:
                        logger.error("发送时出错：")
                        logger.error(e)
                        await app.sendFriendMessage(account, MessageChain.create([Plain("发送时出错，具体类型请看日志，等待450s重试")]))
                        await asyncio.sleep(450)
                        await send_msg_list(msg_list)
    else:
        logger.info("不进行更新")


@channel.use(ListenerSchema(
    listening_events=[FriendMessage],
    inline_dispatchers=[Kanata([FullMatch(".pixauto"), RequireParam("code")])]
))
async def set_auto_pix(app: GraiaMiraiApplication, friend: Friend, code: MessageChain):
    if friend.id == master_id:
        commond = code.asDisplay().strip()
        if commond == "0":
            pix.auto = False
            await app.sendFriendMessage(friend, MessageChain.create([Plain("自动更新已关闭")]))
        if commond == "1":
            pix.auto = True
            await app.sendFriendMessage(friend, MessageChain.create([Plain("自动更新已开启")]))

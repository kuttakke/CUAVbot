import asyncio
from graia.saya import Saya
from graia.broadcast import Broadcast
from graia.saya.builtins.broadcast import BroadcastBehaviour
from graia.scheduler import GraiaScheduler
from graia.scheduler.saya import GraiaSchedulerBehaviour
from graia.application.entry import (
    GraiaMiraiApplication, Session
)
from utils import ModuleLoader, BotAttributes
from utils import logger

loop = asyncio.get_event_loop()
broadcast = Broadcast(loop=loop)
scheduler = GraiaScheduler(loop, broadcast)
saya = Saya(broadcast)

bot = BotAttributes("./config.json")

saya.install_behaviours(BroadcastBehaviour(broadcast))
saya.install_behaviours(GraiaSchedulerBehaviour(scheduler))

ModuleLoader.load(saya)

app = GraiaMiraiApplication(
    broadcast=broadcast,
    connect_info=Session(
        host=bot.host,
        authKey=bot.authKey,
        account=bot.account,
        websocket=True
    ),
    logger=logger
)

try:
    app.launch_blocking()
except KeyboardInterrupt:
    exit()

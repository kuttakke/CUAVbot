from asyncio import sleep
from pathlib import Path
from time import perf_counter

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Plain, Source
from graia.ariadne.message.parser.twilight import (
    MatchResult,
    RegexMatch,
    SpacePolicy,
    Twilight,
    WildcardMatch,
)
from graiax.playwright import PlaywrightBrowser
from graiax.shortcut.saya import decorate, dispatch, listen
from launart.manager import Launart
from playwright._impl._api_types import TimeoutError

from core.control import Controller, Modules
from core.depend.blacklist import BlackList
from utils.tool import to_module_file_name

module_name = "明日方舟干员搜索器"

module = Modules(
    name=module_name,
    file_name=to_module_file_name(Path(__file__)),
    author="Kutake",
    description="使用playwright进行截图,网站为明日方舟wiki:https://prts.wiki/",
    usage=".查询干员 干员名 或 .cxgy 干员名",
)
channel = Controller.module_register(module)


Search = Twilight(
    [
        RegexMatch(r"^[.!。！]((查询干员)|(干员查询)|(cxgy)|(gycx))").space(SpacePolicy.FORCE),
        WildcardMatch(greed=False) @ "operator",
    ]
)


@listen(GroupMessage)
@dispatch(Search)
@decorate(BlackList.require(module_name))
async def search_operator(
    app: Ariadne, group: Group, souce: Source, operator: MatchResult
):
    start_time = perf_counter()
    await app.send_group_message(group, MessageChain("查询并生成图片中，请耐心等待哦~❤"))
    bro = Launart.current().get_interface(PlaywrightBrowser)
    page = None
    try:
        page = await bro.new_page()
        res = await page.goto(
            f"https://prts.wiki/w/{operator.result.display.strip()}",  # type: ignore
            wait_until="load",
            timeout=20000,
        )
        if res and res.status != 200:
            await app.send_group_message(
                group, MessageChain("404了，真的有这个干员存在吗🤔"), quote=souce
            )
            await page.close()
            return
        for _ in range(14):
            await page.mouse.wheel(delta_x=0, delta_y=500)
        await sleep(3)
        card = await page.query_selector(".mw-parser-output")
        assert card
        img = await card.screenshot(type="jpeg", quality=90)
        await app.send_group_message(
            group,
            MessageChain(
                [
                    Plain(f"本次查询共耗时：{'%.4f' % (perf_counter()-start_time)}s"),
                    Image(data_bytes=img),
                ]
            ),
        )
    except TimeoutError:
        await app.send_group_message(group, MessageChain("查询操作超时😢"), quote=souce)
    except Exception as e:
        await app.send_group_message(group, MessageChain("查询发生了未知错误😢"), quote=souce)
        raise e
    finally:
        if page:
            await page.close()

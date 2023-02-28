import contextlib
import itertools
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

from bilireq.grpc.dynamic import grpc_get_user_dynamics
from bilireq.grpc.protos.bilibili.app.dynamic.v2.dynamic_pb2 import (
    DynamicItem,
    DynamicType,
    DynModuleType,
    DynSpaceRsp,
)
from bilireq.utils import post
from graia.ariadne import Ariadne
from graia.ariadne.entry import MessageChain
from graia.ariadne.message.element import Image, Plain
from graiax.playwright.interface import PlaywrightBrowser, PlaywrightContext
from loguru import logger

from utils.msgtool import send_group

from .entity import DynamicImage, DynamicLog
from .service import add_dynamic_log, get_sub_group, is_updated_dynamic

error_path = Path(__file__).parent / "error"
error_path.mkdir(parents=True, exist_ok=True)


class Sub:
    def __init__(self, target: int, sub_type: Literal["dynamic", "live"]) -> None:
        self.target = target
        self.sub_type: Literal["dynamic", "live"] = sub_type
        self.offset = 0
        self.is_updating = False
        self.is_first = True

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, Sub):
            return self.target == __o.target and self.sub_type == __o.sub_type
        return False

    async def get_dynamic(self) -> list[DynamicItem]:
        resp: DynSpaceRsp = await grpc_get_user_dynamics(self.target)
        exclude_list = [
            DynamicType.ad,
            DynamicType.live,
            DynamicType.live_rcmd,
            DynamicType.banner,
        ]
        dynamic_list = [dyn for dyn in resp.list if dyn.card_type not in exclude_list]
        dynamic_list.reverse()
        return dynamic_list

    async def to_card_screen_shot(self, log: DynamicLog) -> bytes | None:
        app = Ariadne.current()
        app.service.manager
        dynid = log.id
        st = int(time.time())
        device = app.launch_manager.get_interface(
            PlaywrightContext
        ).service.playwright.devices["Galaxy S5"]
        browser_context = await app.launch_manager.get_interface(
            PlaywrightBrowser
        ).new_context(**device)
        for i in range(3):
            page = await browser_context.new_page()
            try:
                await page.goto(f"https://m.bilibili.com/dynamic/{dynid}")
                await page.wait_for_load_state("networkidle")
                card = await page.query_selector(".dyn-card")
                assert card
                return await card.screenshot(type="jpeg", quality=90)
            except AssertionError:
                logger.exception(f"[BiliBili推送] {dynid} 动态截图失败，正在重试：")
                await page.screenshot(
                    path=f"{error_path}/{dynid}_{i}_{st}.jpg",
                    full_page=True,
                    type="jpeg",
                    quality=80,
                )
            except Exception as e:  # noqa
                if "bilibili.com/404" in page.url:
                    logger.error(f"[Bilibili推送] {dynid} 动态不存在")
                    break
                elif "waiting until" in str(e):
                    logger.error(f"[BiliBili推送] {dynid} 动态截图超时，正在重试：")
                else:
                    logger.exception(f"[BiliBili推送] {dynid} 动态截图失败，正在重试：")
                    await page.screenshot(
                        path=f"{error_path}/{dynid}_{i}_{st}.jpg",
                        full_page=True,
                        type="jpeg",
                        quality=80,
                    )
            finally:
                with contextlib.suppress():
                    await page.close()

    async def make_dynamic(self, dynamic_list: list[DynamicItem]) -> list[DynamicLog]:
        up_name = dynamic_list[0].modules[0].module_author.author.name
        up_icon = dynamic_list[0].modules[0].module_author.author.face
        up_id: int = dynamic_list[0].extend.uid
        out_list = []
        for dynamic in dynamic_list:
            dyid = int(dynamic.extend.dyn_id_str)

            if dyid <= self.offset or await is_updated_dynamic(dyid):
                continue
            desc = " ".join(
                [
                    x.module_desc.text
                    for x in dynamic.modules
                    if x.module_type == DynModuleType.module_desc
                ]
            )
            img_list = []
            for card in dynamic.modules:
                if card.module_type == DynModuleType.module_dynamic:
                    img_list.extend(i.src for i in card.module_dynamic.dyn_draw.items)
                    break
            out_list.append(
                DynamicLog(
                    id=dyid,
                    type=dynamic.card_type,
                    up_id=up_id,
                    up_name=up_name,
                    up_icon=up_icon,
                    dyn_desc=desc,
                    imgs=[DynamicImage(url=i, did=dyid) for i in img_list],
                    create_time=datetime.now(),
                )
            )
        self.offset = max(
            self.offset, max(int(i.extend.dyn_id_str) for i in dynamic_list)
        )
        return out_list

    async def _to_img(self, dynamic: DynamicLog) -> bytes | None:
        return await self.to_card_screen_shot(dynamic)

    async def to_msg(self, dynamic: DynamicLog) -> MessageChain:
        img = await self._to_img(dynamic)
        return (
            MessageChain(
                [
                    Plain(f"up {dynamic.up_name}（{dynamic.up_id}）有新动态！\n"),
                    Image(data_bytes=img),
                    Plain(await get_b23_url(f"https://t.bilibili.com/{dynamic.id}")),
                ]
            )
            if img
            else MessageChain(
                f"[BiliBili推送] {dynamic.id} | {dynamic.up_name}({dynamic.up_id}) 更新了动态，截图失败"
            )
        )

    @contextlib.asynccontextmanager
    async def _with_update(self):
        self.is_updating = True
        try:
            yield
        finally:
            self.is_updating = False
            self.is_first = False

    async def run(self):
        if self.is_updating:
            return
        async with self._with_update():
            dynamic_list = await self.get_dynamic()
            log = await self.make_dynamic(dynamic_list)
            if not log:
                return
            if not self.is_first:
                msg = [await self.to_msg(i) for i in log]
                sub_group = await get_sub_group(self.target, self.sub_type)
                for m, g in itertools.product(msg, sub_group):
                    await send_group(target=g, msg=m)

            for i in log:
                await add_dynamic_log(i)


async def get_b23_url(burl: str) -> str:
    """
    b23 链接转换

    Args:
        burl: 需要转换的 BiliBili 链接
    """
    url = "https://api.bilibili.com/x/share/click"
    data = {
        "build": 6700300,
        "buvid": 0,
        "oid": burl,
        "platform": "android",
        "share_channel": "COPY",
        "share_id": "public.webview.0.0.pv",
        "share_mode": 3,
    }
    resp = await post(url, data=data)
    return resp["content"]


class Notfound(Exception):
    pass

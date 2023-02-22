import asyncio
import re
import sys
import time
import zipfile
from asyncio import sleep, to_thread
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Coroutine, Literal, NamedTuple, Sequence, Tuple, Union

import aiofile
import imageio
from graia.ariadne import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Element, Image, Plain
from loguru import logger
from pixivpy_async import AppPixivAPI
from pixivpy_async.error import PixivError

from config import settings
from utils.func_retry import aretry
from utils.msgtool import send_debug, send_friend
from utils.session import Session

from .entity import PixivMetaPage, PixivTag, PixivUser, PixivWork
from .service import Curd
from .TokenHandler import TokenHandler


class WorkPage(NamedTuple):
    """作品页"""

    is_gif: bool
    pages: list[PixivMetaPage]
    delay: Sequence[int] | None


@dataclass
class User:
    """用户, qq与pix账号绑定"""

    qq_id: int
    access_token: str
    refresh_token: str
    api: AppPixivAPI
    create_date: datetime
    is_active: bool = True
    offset: int | None = None
    block_tags: list[str] = field(default_factory=list)
    last_update: datetime | None = None

    async def status(self) -> str:
        work_num, page_num = await Curd.get_pixiv_update_work_and_page_num(
            self.qq_id
        )  # type: ignore
        running_time = ""
        if self.last_update:
            time_difference = time.time() - time.mktime(self.last_update.timetuple())
            day = int(time_difference / 86400)
            hour = int(time_difference % 86400 / 3600)
            minute = int(time_difference % 86400 % 3600 / 60)
            second = int(time_difference % 86400 % 3600 % 60)
            running_time = (
                f"{f'{day}d ' if day else ''}{f'{hour}h ' if hour else ''}"
                f"{f'{minute}m ' if minute else ''}{second}s"
            )

        return (
            f"您的账号创建于：{self.create_date}\n"
            f"共发送更新作品{work_num}个，图片{page_num}张\n"
            f"订阅启动状态：{'已开启' if self.is_active else '已关闭'}\n"
            f"{f'已屏蔽tag：{str(self.block_tags)}' if self.block_tags else '无屏蔽tag'}\n"
            f"{f'离上次更新已过：{running_time}' if self.last_update else '无上次更新记录，bot可能在半个小时左右前重启过'}"
        )

    @classmethod
    async def _create(cls, qq_id: int, access_token, refresh_token) -> "User":
        dt = datetime.now()
        await Curd.insert_pixiv_account(qq_id, access_token, refresh_token, dt)
        api = AppPixivAPI(
            proxy=f"{settings.proxy.type}://{settings.proxy.host}:{settings.proxy.port}"
        )
        api.set_auth(access_token, refresh_token)
        return cls(qq_id, access_token, refresh_token, api, dt)

    @classmethod
    async def create_by_token(
        cls, qq_id: int, refresh_token: str
    ) -> Union["User", list[Element]]:
        exists_flag = await Curd.get_pixiv_account_by_qqid(qq_id)
        if exists_flag:
            return [Plain("your account already exists")]
        access_token, refresh_token = await TokenHandler.refresh_token(refresh_token)
        return await cls._create(qq_id, access_token, refresh_token)

    @classmethod
    async def get_all_users(cls) -> list["User"]:
        users = await Curd.get_all_pixiv_account()
        out_list = []
        for i in users:
            api = AppPixivAPI(
                proxy=f"{settings.proxy.type}://{settings.proxy.host}:{settings.proxy.port}"
            )
            api.set_auth(i.access_token, i.refresh_token)
            out_list.append(cls(**i.dict(), api=api))
        return out_list

    async def deactivate(self):
        await Curd.update_pixiv_account(self.qq_id, {"is_active": False})
        self.is_active = False

    async def activate(self):
        await Curd.update_pixiv_account(self.qq_id, {"is_active": True})
        self.is_active = True

    async def refresh(self):
        access_token, refresh_token = await TokenHandler.refresh_token(
            self.refresh_token
        )
        await Curd.update_pixiv_account(
            self.qq_id,
            {"access_token": access_token, "refresh_token": refresh_token},
        )
        self.refresh_token = refresh_token
        self.access_token = access_token
        self.api.set_auth(access_token, refresh_token)

    async def destroy(self):
        await Curd.delete_pixiv_account(self.qq_id)

    async def add_block_tag(self, tag_name: str) -> bool:
        exists = await Curd.get_pixiv_block_tag_by_qqid_and_name(self.qq_id, tag_name)
        if exists:
            return False
        await Curd.insert_pixiv_block_tag(self.qq_id, tag_name)
        self.block_tags.append(tag_name)
        return True

    async def del_block_tag(self, tag_name: str) -> bool:
        exists = any(i == tag_name for i in self.block_tags)
        if exists:
            await Curd.delete_pixiv_block_tag(self.qq_id, tag_name)
            self.block_tags.remove(tag_name)
            return True
        return False

    async def nsfw_switch(self, is_active: bool) -> bool:
        if is_active:
            return await self.add_block_tag("R-18")
        else:
            return await self.del_block_tag("R-18")

    @aretry()
    async def _fetch_artflow(self) -> dict:
        json_all: dict = await self.api.illust_follow(offset=self.offset)  # type: ignore
        if "error" in json_all:
            await self.refresh()
            # logger.info(
            #     "[AutoPix]Failed to fetch subscribed artwork, refresh token completed"
            # )
            raise RuntimeError("Failed to fetch subscribed artwork")
        return json_all

    async def _ugoira_info(
        self, pid: int, _retry_times: int = 0
    ) -> tuple[str, str, list[int]]:
        """
        get ufoira metadata by pid, will retry in _retry_times
        :param pid:
        :param _retry_times:
        :return:original, large, frame
        """
        data = None
        try:
            data = await self.api.ugoira_metadata(pid)
        except Exception as e:
            logger.error(f"request ugoira_error: {e}")
            if _retry_times >= 3:
                if data:
                    logger.info(f"now ugoira data: {data}")
                raise e
            return await self._ugoira_info(pid, _retry_times + 1)
        else:
            if "error" in data and _retry_times <= 3:
                await self.refresh()
                # logger.info("[AutoPix]token out of expiration_date, refresh completed")
                return await self._ugoira_info(pid, _retry_times + 1)
            elif "error" in data:
                raise ValueError(
                    f"[AutoPix]error when fetch illust_follow, json data: {data}"
                )
            frame = [i["delay"] / 1000 for i in data["ugoira_metadata"]["frames"]]
            large = data["ugoira_metadata"]["zip_urls"]["medium"]
            original = large.replace("600x600", "1920x1080")
            return original, large, frame

    async def _single_user_add(self, user: dict) -> PixivUser:
        """单个用户添加"""
        uid = user["id"]
        name = user["name"]
        parent_path = f"{settings.pix.save_path}/{uid}"
        Path(parent_path).mkdir(parents=True, exist_ok=True)
        pix_user = PixivUser(id=uid, name=name, img_path=parent_path)
        await Curd.insert_pixiv_user(pix_user)
        return pix_user

    async def _single_illust_tags_update(self, tags: dict) -> list[PixivTag]:
        tag_list = []
        for tag in tags:
            if not (t := await Curd.get_pixiv_tag_by_name(tag["name"])):
                t = await Curd.insert_pixiv_tag(tag["name"])
            tag_list.append(t)
        return tag_list

    async def _single_illust_pages_handle(
        self, illust: dict, img_path: str
    ) -> WorkPage:
        if illust["type"] == "ugoira":
            original, large, image_delay = await self._ugoira_info(illust["id"])
            return WorkPage(
                is_gif=True,
                pages=[
                    PixivMetaPage(
                        id=illust["id"],
                        page_count=0,
                        original=original,
                        large=large,
                        square_medium=None,
                        medium=None,
                        path=f"{img_path}/{illust['id']}_p0.gif",
                    )
                ],
                delay=image_delay,
            )
        elif illust["meta_single_page"]:
            file_name = re.findall(
                r"p[0-9]+.[\S]{3}", illust["meta_single_page"]["original_image_url"]
            )[0]
            return WorkPage(
                is_gif=False,
                pages=[
                    PixivMetaPage(
                        **illust["image_urls"],
                        id=illust["id"],
                        page_count=0,
                        original=illust["meta_single_page"]["original_image_url"],
                        path=f"{img_path}/{illust['id']}_{file_name}",
                    )  # type: ignore
                ],
                delay=None,
            )
        else:
            page_list = []
            for count, n in enumerate(illust["meta_pages"]):
                urls = n["image_urls"]
                file_name = re.findall(r"p[0-9]+.[\S]{3}", urls["original"])[0]
                page_list.append(
                    PixivMetaPage(
                        **urls,
                        id=illust["id"],
                        page_count=count,
                        path=f"{img_path}/{illust['id']}_{file_name}",
                    )
                )
            return WorkPage(is_gif=False, pages=page_list, delay=None)

    @staticmethod
    def is_img_type(file_bytes: bytes) -> bool:
        """使用图片文件结尾标识判断是否为图片

        Args:
            file_bytes (bytes): 图片字节

        Returns:
            bool: 是否为图片
        """
        return file_bytes.endswith(b"\xff\xd9") or file_bytes.endswith(b"\xaeB`\x82")

    async def _fetch_illust_img_with_timeout(self, page: PixivMetaPage) -> bytes:
        return await asyncio.wait_for(self._fetch_illust_img(page), timeout=15)

    @aretry()
    async def _fetch_illust_img(self, page: PixivMetaPage) -> bytes:
        """获取图片"""
        if Path(page.path).exists():
            async with aiofile.async_open(page.path, "rb") as f:
                return BytesIO(await f.read()).getvalue()

        async with Session.proxy_session.get(
            page.original.replace("i.pximg.net", "i.pixiv.re")
        ) as resp:
            img = BytesIO(await resp.read()).getvalue()
            real_size = sys.getsizeof(img)
            if not resp.headers.get("Content-Length"):
                content_length = real_size
                # logger.debug(res.headers)
                # File integrity verification is not enforced，Warning only
                logger.warning(
                    "[AutoPix]no Content-Length, Unable to ensure file integrity"
                )
            else:
                content_length = int(resp.headers.get("Content-Length"))  # type: ignore
        if content_length - real_size > 1024:
            raise PixivError("File size mismatch")
        if not self.is_img_type(img) and Path(page.path).suffix not in (".gif",):
            raise PixivError("File type error")
        # logger.info(f"[AutoPix]Fetch illust img success: {page.path}")
        return img

    def _gif_handle(self, page: PixivMetaPage, img: bytes, delay: Sequence[int]):
        """处理动图"""
        zip_file = zipfile.ZipFile(BytesIO(img), "r")
        image_pic = []
        for name in zip_file.namelist():
            pic = zip_file.read(name)
            image_pic.append(imageio.imread(pic))
        # it runs write first then read which is not needed, don't know how to optimize it
        imageio.mimsave(page.path, image_pic, "GIF", duration=delay)  # type: ignore
        return BytesIO(Path(page.path).read_bytes()).read()

    async def _send_img(self, page: PixivMetaPage, img: bytes):
        if page.page_count == 0:
            msg = MessageChain([Plain(f"pid: {page.id}"), Image(data_bytes=img)])
        else:
            msg = MessageChain(Image(data_bytes=img))
        await send_friend(self.qq_id, msg)

    async def _send_image(
        self, pages: Sequence[PixivMetaPage], img_list: Sequence[bytes]
    ):
        """发送图片"""
        for page, img in zip(pages, img_list):
            try:
                await self._send_img(page, img)
            except Exception as e:
                file_name = Path(page.path).name
                if "file size over max" in str(e):
                    e = "文件过大/file size over max"
                logger.error(f"[AutoPix]Send {file_name} error: {e}")
                await send_friend(self.qq_id, f"[AutoPix]发送{file_name}报错: {e}")
                await send_debug(f"[AutoPix]Send {file_name} error: {e}")

    async def _fetch_and_send(
        self,
        pages: Sequence[PixivMetaPage],
        delay: Union[Sequence[int], None] = None,
    ):
        """获取图片并发送"""
        if delay:
            img = await to_thread(
                self._gif_handle,
                pages[0],
                await self._fetch_illust_img(pages[0]),
                delay,
            )
            await self._send_image(pages, [img])
        else:
            img_list = await asyncio.gather(  # NOTE - may cause memory leak or too many open sockets
                *[
                    asyncio.ensure_future(self._fetch_illust_img_with_timeout(page))
                    for page in pages
                ],
                return_exceptions=True,
            )
            if any(isinstance(img, Exception) for img in img_list):
                logger.error(f"[AutoPix]Fetch pid:{pages[0].id} imgs error; pass")
                raise PixivError("Fetch imgs error")
            await self._send_image(pages, img_list)

    async def _get_user(self, illust: dict) -> PixivUser:
        """获取用户"""
        if not (pix_user := await Curd.get_pixiv_user_by_id(illust["user"]["id"])):
            pix_user = await self._single_user_add(illust["user"])
        return pix_user

    def _is_block_tags(self, tags: list[PixivTag]) -> bool:
        # sourcery skip: use-any
        """是否包含屏蔽标签"""
        return next(
            (True for tag in self.block_tags if tag in [t.name for t in tags]),
            False,
        )

    def _get_fetch_func(
        self,
        pages: WorkPage,
    ) -> Coroutine[Any, Any, None]:
        """获取获取图片函数"""
        return (
            self._fetch_and_send(pages.pages, pages.delay)
            if pages.is_gif
            else self._fetch_and_send(pages.pages)
        )

    async def _single_illust_update(self, illust: dict) -> None:
        """单个作品更新"""
        pid = illust["id"]
        if await Curd.get_pixiv_work_by_id(pid):
            return
        pix_user = await self._get_user(illust)
        tag_list = await self._single_illust_tags_update(illust["tags"])
        if self._is_block_tags(tag_list):
            return
        page_list = await self._single_illust_pages_handle(illust, pix_user.img_path)
        func = self._get_fetch_func(page_list)
        try:
            await func
        except Exception as e:
            UserHandler.set_status(pid, "error")
        else:
            work = PixivWork(
                id=pid,
                title=illust["title"],
                type=illust["type"],
                user_id=pix_user.id,
                create_date=datetime.fromtimestamp(
                    time.mktime(
                        time.strptime(
                            illust["create_date"].split("+")[0].replace("T", " "),
                            "%Y-%m-%d %H:%M:%S",
                        )
                    )
                    - 3600
                ),
                page_count=len(page_list.pages),
                tags=tag_list,
                meta_pages=page_list.pages,
                user=pix_user,
            )
            await Curd.insert_pixiv_work(work, self.qq_id)
            UserHandler.set_status(pid, "success")

    async def run_update(self):
        """pix更新，侧重单个作品处理并下载→单个作品发送→单个作品数据库存储 这样的流程，而非大方法+数个大循环+大量冗余的局部变量， 并跳过有图片下载失败的作品

        Args:

        Returns:
            _type_: _description_

        Yields:
            _type_: _description_
        """
        data = await self._fetch_artflow()
        for illust in data["illusts"]:
            await self._single_illust_update(illust)


class UserHandler:
    """控制用户行为类, 包括对应行为的消息回复"""

    user_all: dict[int, "User"] = {}
    last_send_info = ""
    is_updating = False
    _update_status: dict[int, Literal["success", "error"]] = {}
    _time_cost = 0

    @classmethod
    async def init_user(cls):
        """拿到所有user"""

        user_list = await User.get_all_users()
        for user in user_list:
            cls.user_all.update({user.qq_id: user})
        logger.info(f"[AutoPix] 初始化完成, 共有{len(user_list)}个用户")

    @classmethod
    @asynccontextmanager
    async def get_db_and_client(cls):
        """控制is_updating"""
        cls.is_updating = True
        try:
            yield
        finally:
            cls.is_updating = False

    @classmethod
    async def _send_info_to_debug_group(cls, text: str):
        """发送debug消息"""
        app = Ariadne.current()
        await app.send_group_message(settings.mirai.debug_group, MessageChain(text))

    @classmethod
    async def _send_info_to_user(cls, user: "User", text: str):
        app = Ariadne.current()
        await app.send_friend_message(user.qq_id, MessageChain(text))

    @classmethod
    async def _send_message_with_retry(
        cls, qq_id: int, msg: list[Plain | Image] | Image, _retry: bool = False
    ):
        """发送更新"""
        app = Ariadne.current()
        try:
            if isinstance(msg, list):
                cls.last_send_info: str = msg[0].text.replace("\n", "")  # type: ignore
            await app.send_friend_message(qq_id, MessageChain(msg))
        except Exception as e:
            logger.error(e)
            if _retry:
                if isinstance(msg, list):
                    size = sys.getsizeof(await msg[1].get_bytes())  # type: ignore
                else:
                    size = sys.getsizeof(await msg.get_bytes())
                await app.send_friend_message(
                    qq_id, MessageChain(f"[AutoPix]发送失败，错误为：{e}")
                )
                logger.error(f"[AutoPix] fileSize：{size} info: {cls.last_send_info}")
                await cls._send_info_to_debug_group(
                    f"@{qq_id}的单个图片发送出现错误:{e}\n"
                    f"最后存储的pid信息为{cls.last_send_info}\n"
                    f"图片bytes大小为：{size}"
                )
                return
            await sleep(10)
            return await cls._send_message_with_retry(qq_id, msg, _retry=True)

    @classmethod
    def get_all_user(cls) -> list["User"]:
        return list(cls.user_all.values())

    @classmethod
    def add_user(cls, user: "User"):
        cls.user_all.update({user.qq_id: user})

    @classmethod
    def get_user(cls, qq_id: int) -> User | None:
        return cls.user_all.get(qq_id, None)

    @classmethod
    def remove_user(cls, qq_id: int):
        cls.user_all.pop(qq_id)

    @classmethod
    async def update(cls, qq_id: int | None = None):
        start_time = time.perf_counter()
        user = cls.get_user(qq_id)  # type: ignore
        if not user and qq_id:
            return True
        if cls.is_updating:
            await cls._send_info_to_debug_group("[AutoPix]已处于更新状态，取消本次更新")
            if qq_id and user:
                await cls._send_info_to_user(user, "[AutoPix]已处于更新中，取消本次更新")
            return True
        async with cls.get_db_and_client():  # type: ignore
            users = [user] if user else list(cls.user_all.values())
            for i in users:
                if not i.is_active:
                    logger.info(f"[AutoPix] qq:{i.qq_id} disabled, skip")
                    continue
                try:
                    await i.run_update()  # type: ignore
                except Exception as e:
                    logger.exception(e)
                    await cls._send_info_to_debug_group(
                        f"[AutoPix]{i.qq_id}用户更新出现未捕获的错误：{e}"
                    )
        cls._time_cost += time.perf_counter() - start_time

    @classmethod
    def _count_update_status(cls, status: Literal["success", "error"]) -> int:
        return sum(j == status for j in cls._update_status.values())

    @classmethod
    def get_update_status(cls) -> str:
        return (
            f"[AutoPix]今日更新状态：\n"
            f"成功：{cls._count_update_status('success')}\n"
            f"失败：{cls._count_update_status('error')}\n"
            f"耗时：{cls._time_cost:.2f}s"
        )

    @classmethod
    def status_clear(cls):
        cls._update_status.clear()
        cls._time_cost = 0

    @classmethod
    def set_status(cls, work_id: int, status: Literal["success", "error"]):
        cls._update_status.update({work_id: status})

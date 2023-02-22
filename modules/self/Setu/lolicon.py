import asyncio
import json
from io import BytesIO
from time import perf_counter
from typing import Sequence

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from aiohttp.http_exceptions import HttpProcessingError
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Plain
from loguru import logger

from utils import aretry
from utils.msgtool import make_forward_msg
from utils.session import Session


class LoliconApi:
    url = "https://api.lolicon.app/setu/v2"
    # proxy = "i.pixiv.re"  # looks like error
    proxy = "i.pixiv.re"
    timeout = 10
    numbers = {
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "⑨": 9,
    }

    @staticmethod
    def is_img_type(file_bytes: bytes) -> bool:
        """使用图片文件结尾标识判断是否为图片

        Args:
            file_bytes (bytes): 图片字节

        Returns:
            bool: 是否为图片
        """
        return file_bytes.endswith(b"\xff\xd9") or file_bytes.endswith(b"\xaeB`\x82")

    @classmethod
    @aretry(times=2, exceptions=(ClientError, HttpProcessingError))
    async def fetch(cls, session: ClientSession, param: dict) -> dict:
        async with session.post(
            url=cls.url,
            data=json.dumps(param),
            headers={"Content-Type": "application/json"},
        ) as res:
            return await res.json()

    @classmethod
    @aretry(exceptions=(ClientError, HttpProcessingError))
    async def fetch_img(cls, session: ClientSession, url: str) -> bytes:
        async with session.get(url=url) as res:
            img_bytes = BytesIO(await res.read()).read()
        if not cls.is_img_type(img_bytes):
            raise ClientError("图片类型错误")
        return img_bytes

    @classmethod
    def _semantic_comment_to_data(cls, comment: str) -> dict:
        data = {}
        numbers = cls.numbers.get(comment[1], False)
        if comment[1].isnumeric():
            data["num"] = numbers or int(comment[1])
            comment = comment[3:]
        elif numbers:
            data["num"] = numbers
            comment = comment[3:]
        else:
            comment = comment[2:]
        if "的" in comment:
            comment = comment[:-5] if "setu" in comment else comment[:-3]
            data["tag"] = comment
        return data

    @classmethod
    def _comment_to_data(cls, comment: str) -> dict:
        data = {}
        comment_list = comment.split()
        if len(comment_list) == 1:
            return data
        else:
            comment_list = comment_list[1:]
        if comment_list[0].isnumeric():
            num = int(comment_list[0])
            if 0 < num < 10:
                data["num"] = num
            comment_list.remove(comment_list[0])
        if comment_list:
            comment = comment_list[0]
            tags_list = []
            for i in comment.split("&"):
                or_list = i.split("|")
                if not or_list:
                    continue
                if len(or_list) == 1:
                    tags_list.append(or_list[0])
                else:
                    tags_list.append(list(or_list))
            if tags_list:
                data["tag"] = tags_list
        return data

    @classmethod
    def _make_param(cls, comment: str, nsfw: int = 0, semantic: bool = True) -> dict:
        data = {
            "r18": nsfw,
            "num": 1,
            "proxy": cls.proxy,
        }
        if semantic:
            param = cls._semantic_comment_to_data(comment)
        else:
            param = cls._comment_to_data(comment)
        if param:
            data |= param
        logger.info(f"[Setu]new setu request:{data}")
        return data

    @classmethod
    def _is_all_excp(cls, bytes_list: Sequence[bytes | BaseException]) -> bool:
        return all(isinstance(i, BaseException) for i in bytes_list)

    @classmethod
    async def _to_msg(
        cls,
        url_list: list[str],
        pid_list: list[str],
        start_time: float = perf_counter(),
    ) -> MessageChain:
        if len(url_list) == 1:
            img = await cls.fetch_img(Session.proxy_session, url_list[0])
            return MessageChain([Plain(f"pid：{pid_list[0]}"), Image(data_bytes=img)])
        bytes_list = await asyncio.gather(
            *[
                asyncio.ensure_future(cls.fetch_img(Session.proxy_session, url))
                for url in url_list
            ],
            return_exceptions=True,
        )
        if cls._is_all_excp(bytes_list):
            return MessageChain("图片获取失败")
        msg_list = [
            MessageChain([Plain(f"pid：{pid}\n"), Image(data_bytes=img)])
            if isinstance(img, bytes)
            else MessageChain(f"pid：{pid}\n图片获取失败:{img}")
            for pid, img in zip(pid_list, bytes_list)
        ]
        msg_list.insert(0, MessageChain(f"耗时：{perf_counter() - start_time:.2f}s\n"))
        return MessageChain(make_forward_msg(msg_list))

    @classmethod
    async def run(
        cls, comment: str, nsfw: int = 0, semantic: bool = True
    ) -> MessageChain:
        """根据参数获取图片

        Args:
            comment (str): 命令
            nsfw (int, optional): 0正常, 1NSFW, 2混合. Defaults to 0.
            semantic (bool, optional): 命令是否语义化. Defaults to True.

        Returns:
            MessageChain: _description_
        """
        start = perf_counter()
        data = cls._make_param(comment, nsfw, semantic)
        res = await cls.fetch(Session.proxy_session, data)
        if res.get("error", None):
            return MessageChain(f"遇到了错误！\n{res.get('error')}")
        data_list = res["data"]
        return await cls._to_msg(
            [i["urls"]["original"] for i in data_list],
            [i["pid"] for i in data_list],
            start,
        )

import asyncio
from time import perf_counter
from typing import Type

from aiohttp.client import ClientSession
from aiohttp.client_exceptions import ClientError
from aiohttp.http_exceptions import HttpProcessingError
from graia.ariadne.entry import Image, MessageChain, Plain
from loguru import logger
from PicImageSearch import Ascii2D, BaiDu, EHentai, Google, Iqdb, Network, SauceNAO
from PicImageSearch.network import HandOver

from config import settings
from utils import aretry
from utils.msgtool import make_forward_msg


class Searcher:
    @classmethod
    @property
    def _network(cls):
        return Network(
            proxies=f"{settings.proxy.type}://{settings.proxy.host}:{settings.proxy.port}"
        )

    @classmethod
    async def _msg(cls, engine: HandOver, resp_item):
        return MessageChain(
            [
                Plain(f"搜图引擎: {engine.__class__.__name__}\n"),
                Plain(
                    f"标题: {resp_item.title}\n"
                    if hasattr(resp_item, "title") and resp_item.title
                    else ""
                ),
                Image(data_bytes=await engine.download(resp_item.thumbnail)),
                Plain("\n"),
                Plain(
                    f"相似度: {resp_item.similarity}%\n"
                    if hasattr(resp_item, "similarity") and resp_item.similarity
                    else ""
                ),
                Plain(
                    f"作者: {resp_item.author}\n"
                    if hasattr(resp_item, "author") and resp_item.author
                    else ""
                ),
                Plain(
                    f"来源: {resp_item.source}\n"
                    if hasattr(resp_item, "source") and resp_item.source
                    else ""
                ),
                Plain(
                    f"链接: {resp_item.url}\n"
                    if hasattr(resp_item, "url") and resp_item.url
                    else ""
                ),
            ]
        )

    @classmethod
    @aretry(times=2, exceptions=(ClientError, HttpProcessingError))
    async def _handler(
        cls,
        client: ClientSession,
        url: str,
        engine: Type[SauceNAO]
        | Type[Ascii2D]
        | Type[BaiDu]
        | Type[EHentai]
        | Type[Google]
        | Type[Iqdb],
    ) -> list[MessageChain]:
        if engine == SauceNAO:
            engine_ = engine(client=client, api_key=settings.saucenao.api_key)
        else:
            engine_ = engine(client=client)
        resp = await engine_.search(url)
        if not resp.raw:
            return [MessageChain(f"搜图引擎{engine_.__class__.__name__}未找到结果")]
        if engine == Ascii2D and not resp.raw[0].title:  # type: ignore
            resp.raw = resp.raw[1:]  # type: ignore
        if engine == Google:
            resp.raw = resp.raw[2:]  # type: ignore
        if hasattr(resp.raw[0], "similarity") and resp.raw[0].similarity < 70:  # type: ignore
            return [await cls._msg(engine_, resp.raw[0])]

        return [await cls._msg(engine_, item) for item in resp.raw[:2]]

    @classmethod
    async def _exc_handler(
        cls,
        client: ClientSession,
        url: str,
        engine: Type[SauceNAO]
        | Type[Ascii2D]
        | Type[BaiDu]
        | Type[EHentai]
        | Type[Google]
        | Type[Iqdb],
    ) -> list[MessageChain]:
        try:
            return await cls._handler(client, url, engine)
        except Exception as e:
            logger.exception(e)
            if isinstance(e, (ClientError, HttpProcessingError)):
                return [MessageChain(Plain(f"{engine.__name__}网络错误"))]
            return [MessageChain(Plain(f"{engine.__name__}未知错误 {e}"))]

    @classmethod
    async def waifu(cls, url: str) -> MessageChain:
        start = perf_counter()
        async with cls._network as client:
            res1, res2, res3 = await asyncio.gather(
                *[
                    asyncio.ensure_future(cls._exc_handler(client, url, engine))
                    for engine in [SauceNAO, Ascii2D, Iqdb]
                ]
            )
        all_msg = res1 + res2 + res3
        if len(all_msg) == 3 and all("错误" in msg for msg in all_msg):
            return MessageChain("搜图出现错误😢")
        return MessageChain(
            make_forward_msg(
                [MessageChain(f"共耗费{perf_counter()-start:.2f}s"), *all_msg]
            )
        )

    @classmethod
    async def google_baidu(cls, url: str) -> MessageChain:
        start = perf_counter()
        async with cls._network as client:
            res1, res2 = await asyncio.gather(
                *[
                    asyncio.ensure_future(cls._exc_handler(client, url, engine))
                    for engine in [Google, BaiDu]
                ]
            )
        return MessageChain(
            make_forward_msg(
                [MessageChain(f"共耗费{perf_counter()-start:.2f}s"), *res1, *res2]
            )
        )

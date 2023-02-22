from typing import Literal, overload

import aiohttp
from aiohttp_proxy import ProxyConnector, ProxyType
from loguru import logger

from config import settings


class Session:
    # 统一管理session
    # 多账号同一session可能导致cookies失效
    _proxy_session: None | aiohttp.ClientSession = None
    _session: None | aiohttp.ClientSession = None

    @classmethod
    @property
    def proxy_session(cls) -> aiohttp.ClientSession:
        if not cls._proxy_session:
            cls._proxy_session = aiohttp.ClientSession(
                connector=ProxyConnector(
                    proxy_type=ProxyType.SOCKS5,
                    host=settings.proxy.host,
                    port=settings.proxy.port,
                    # rdns=True,
                )
            )
        return cls._proxy_session

    @classmethod
    @property
    def session(cls) -> aiohttp.ClientSession:
        if not cls._session:
            cls._session = aiohttp.ClientSession()
        return cls._session

    @classmethod
    async def close(cls):
        if cls._session:
            await cls._session.close()
        if cls._proxy_session:
            await cls._proxy_session.close()

    @overload
    @classmethod
    async def request(
        cls,
        method: str,
        url: str,
        *,
        proxy: bool = False,
        response_type="json",
        __retry: int = 0,
        **kwargs,
    ) -> dict:
        ...

    @overload
    @classmethod
    async def request(
        cls,
        method: str,
        url: str,
        *,
        proxy: bool = False,
        response_type="text",
        __retry: int = 0,
        **kwargs,
    ) -> str:
        ...

    @overload
    @classmethod
    async def request(
        cls,
        method: str,
        url: str,
        *,
        proxy: bool = False,
        response_type="bytes",
        __retry: int = 0,
        **kwargs,
    ) -> bytes:
        ...

    @classmethod
    async def request(
        cls,
        method: str,
        url: str,
        *,
        proxy: bool = False,
        response_type: str = "json",
        __retry: int = 0,
        **kwargs,
    ) -> dict | str | bytes:
        session = cls.proxy_session if proxy else cls.session
        try:
            async with session.request(method, url, **kwargs) as resp:
                # return resp.json
                if response_type == "json":
                    return await resp.json()
                elif response_type == "text":
                    return await resp.text()
                elif response_type == "bytes":
                    return await resp.read()
                else:
                    raise ValueError("response_type must be json, text or bytes")
        except aiohttp.ClientError as e:
            if __retry < 3:
                return await cls.request(
                    method, url, proxy=proxy, __retry=__retry + 1, **kwargs
                )
            logger.exception(e)
            raise e

    @classmethod
    async def get(
        cls,
        url: str,
        *,
        proxy: bool = False,
        response_type: Literal["json", "text", "bytes"] = "json",
        **kwargs,
    ) -> dict | str | bytes:
        return await cls.request(
            "GET", url, proxy=proxy, response_type=response_type, **kwargs
        )

    @classmethod
    async def post(
        cls,
        url: str,
        *,
        proxy: bool = False,
        response_type: Literal["json", "text", "bytes"] = "json",
        **kwargs,
    ) -> dict | str | bytes:
        return await cls.request(
            "POST", url, proxy=proxy, response_type=response_type, **kwargs
        )

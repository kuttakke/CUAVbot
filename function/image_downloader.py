import os
import aiohttp
from aiohttp_proxy import ProxyConnector, ProxyType
import aiofile
from io import BytesIO

class IDer:
    _path = "./function/pixiv_img"
    _headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
        'referer': 'https://www.pixiv.net/'

    }

    _connector = ProxyConnector(
        proxy_type=ProxyType.SOCKS5,
        host='192.168.0.60',
        port=2089,
    )

    @classmethod
    async def pixiv_downloader(cls, url: str, retry: int = 0):
        name = url.split("/")[-1]
        path = os.path.join(cls._path, name)
        if os.path.exists(path):
            async with aiofile.async_open(path, "rb") as f:
                out = BytesIO(await f.read())
            return out.getvalue()
        try:
            async with aiohttp.request('GET', url, headers=cls._headers) as res:
                img = BytesIO(await res.read())
            # img = requests.get(url, headers=cls._headers, proxies=cls._proxies).content
        except BaseException as e:
            print(e)
            if retry <= 3:
                return await cls.pixiv_downloader(url, retry + 1)
            else:
                return False
        else:
            async with aiofile.async_open(path, "wb") as f:
                await f.write(img.getvalue())
            return img.getvalue()



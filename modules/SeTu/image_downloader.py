import os
import aiofile
import aiosonic
from io import BytesIO


class IDer:
    _headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
        'referer': 'https://www.pixiv.net/'
    }

    @classmethod
    async def pixiv_downloader(
            cls, url: str, img_path: str, retry: int = 0, referer: bool = False, return_type: str = "bytes"
    ):
        """
        pixiv图片下载
        :param url: 目标图片url
        :param img_path: 下载目录
        :param retry: 重试次数
        :param referer: 是否为原连接
        :param return_type: 返回类型，默认为bytes图片;可选 'path'
        :return: img[bytes]/img-path[str]
        """
        name = url.split("/")[-1]
        path = os.path.join(img_path, name)
        if os.path.exists(path):
            if return_type == 'bytes':
                async with aiofile.async_open(path, "rb") as f:
                    out = BytesIO(await f.read())
                return out.getvalue()
            elif return_type == 'path':
                return path
        if referer:
            try:
                # async with aiohttp.request('GET', url, headers=cls._headers) as res:
                #     code = res.status
                #     img = BytesIO(await res.read())
                async with aiosonic.HTTPClient() as client:
                    res = await client.get(url, headers=cls._headers)
                    code = res.status_code
                    img = BytesIO(await res.content())
                # img = requests.get(url, headers=cls._headers, proxies=cls._proxies).content
            except BaseException as e:
                print(e)
                if retry <= 3:
                    return await cls.pixiv_downloader(url, img_path, retry + 1)
                else:
                    return False
            else:
                if code == 200:
                    async with aiofile.async_open(path, "wb") as f:
                        await f.write(img.getvalue())
                    if return_type == 'bytes':
                        return img.getvalue()
                    elif return_type == 'path':
                        return path
                else:
                    return 1
        else:
            try:
                # async with aiohttp.request('GET', url) as res:
                #     img = BytesIO(await res.read())
                async with aiosonic.HTTPClient() as client:
                    res = await client.get(url)
                    code = res.status_code
                    img = BytesIO(await res.content())
                # img = requests.get(url, headers=cls._headers, proxies=cls._proxies).content
            except BaseException as e:
                print(e)
                if retry <= 3:
                    return await cls.pixiv_downloader(url, img_path, retry + 1)
                else:
                    return False
            else:
                if code == 200:
                    async with aiofile.async_open(path, "wb") as f:
                        await f.write(img.getvalue())
                    if return_type == 'bytes':
                        return img.getvalue()
                    elif return_type == 'path':
                        return path
                else:
                    return 1

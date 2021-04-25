import aiosonic
from .image_downloader import IDer


class SeTu:
    def __init__(self, key: str, img_path: str):
        self._url = "https://api.lolicon.app/setu/"
        self._keys = key
        self._img_path = img_path
        self._params = {'apikey': key}
        self._params_r18 = {'apikey': key, "r18": "1"}
        self._params_test = {'apikey': key, 'proxy': 'disable'}

    async def get_setu_with_keyword(self, r18: bool, keyword: str, retry: int = 0,
                                    proxy: bool = False, image_not_found: bool = False):
        """搜索涩图
        :param r18: 是否R18
        :param keyword: 关键词
        :param retry: 当前重试次数，默认为0
        :param proxy: 返回的图片链接是否为原链接，默认为否
        :param image_not_found: 该图片是否存在，True则重试一次，默认为False
        :return: bytes图片
        """
        if r18 is True:
            params = {'apikey': self._keys, "r18": "2", "keyword": keyword, 'proxy': 'disable'}
        else:
            params = {'apikey': self._keys, "r18": "0", "keyword": keyword, 'proxy': 'disable'}
        if not proxy:
            del params['proxy']
        try:
            # async with aiohttp.request('GET', self._url, params=params) as res:
            #     html = await res.text()
            async with aiosonic.HTTPClient() as client:
                res = await client.get(self._url, params=params)
                html = await res.json()
        except BaseException as e:
            print('请求部分出错', e)
            if retry <= 3:
                retry += 1
                return await self.get_setu_with_keyword(r18, keyword, retry)
            else:
                return False
        else:
            # json_text = json.loads(html)["data"]
            json_text = html["data"]
            if len(json_text):
                out = await IDer.pixiv_downloader(json_text[0]["url"], self._img_path)
                if not out:
                    return None
                elif out == 1 and image_not_found is False:
                    return self.get_setu_with_keyword(r18, keyword, retry, proxy, image_not_found=True)
                else:
                    return str(json_text[0]["pid"]), out
            else:
                return None

    # @classmethod
    # async def check_keyword_in_user_set(cls, word):
    #     key_data = await cls.set_user_keyword("r")
    #     for k, v in key_data.items():
    #         if word == k:
    #             return v
    #     return None
    #
    # @classmethod
    # async def set_user_keyword(cls, mode: str, up_data: Optional[dict] = None) -> Optional[dict]:
    #     if mode == "r":
    #         async with aiofile.async_open("./config/user_keyword.json", "r") as f:
    #             data = json.loads(await f.read())
    #         return data
    #     elif mode == "w":
    #         async with aiofile.async_open("./config/user_keyword.json", "w") as f:
    #             await f.write(json.dumps(up_data, indent=4, ensure_ascii=True))
    #         return None
    #
    # @classmethod
    # async def change_user_keyword(cls, data: str):
    #     key_data = await cls.set_user_keyword("r")
    #     list_ = data.split()
    #     key_data.update({list_[0]: list_[1]})
    #     await cls.set_user_keyword("w", key_data)


import requests
import json
import aiohttp
from function.image_downloader import IDer


class SeTu:
    def __init__(self, key: str):
        self._url = "https://api.lolicon.app/setu/"
        self._keys = key
        self._params = {'apikey': key}
        self._params_r18 = {'apikey': key, "r18": "1"}
        self._params_test = {'apikey': key, 'proxy': 'disable'}

    async def get_setu_with_keyword(self, r18: bool, keyword: str, retry: int = 0):
        if r18 is True:
            params = {'apikey': self._keys, "r18": "2", "keyword": keyword, 'proxy': 'disable'}
        else:
            params = {'apikey': self._keys, "r18": "0", "keyword": keyword, 'proxy': 'disable'}
        try:
            async with aiohttp.request('GET', self._url, params=params) as res:
                html = await res.text()
        except BaseException as e:
            print('请求部分出错', e)
            if retry <= 3:
                retry += 1
                return await self.get_setu_with_keyword(r18, keyword, retry)
            else:
                return False
        else:
            json_text = json.loads(html)["data"]
            if len(json_text):
                out = await IDer.pixiv_downloader(json_text[0]["url"])
                if out:
                    return str(json_text[0]["pid"]), out
                else:
                    return None
            else:
                return None

# if __name__ == '__main__':
    # res = await SeTu.get_setu_with_keyword(True, "")
    # if len(res):
    #     print(res)
    # else:
    #     print("None")

import json
from urllib.parse import quote
from graia.application.entry import (
    Image,
    Plain
)
from bs4 import BeautifulSoup as bs
from bs4.element import Tag
from saucenao_api import SauceNao as SN
import aiohttp
from aiohttp_proxy import ProxyConnector, ProxyType
from typing import List


class FaShu:
    @classmethod
    def search_fashu(cls, dic: dict, fashu: str) -> str:
        word = fashu.replace(".mf", "").replace("。mf", "").strip()
        for i in dic.keys():
            if word in i:
                return i + dic[i]
        return "无结果请确认名称"

    @classmethod
    def set_fashu(cls) -> dict:
        with open(r"./dnd/Fashu2_0.json", "r", encoding="utf-8") as f:
            dic = json.loads(f.read())
        return dic

    @classmethod
    def search_image_f(cls, dic: dict, fashu: str):
        word = fashu.replace(".mf", "").replace("。mf", "").strip()
        title = list(dic.keys())
        count = 1
        for i in title:
            if word in i:
                file_name = "./function/text_to_img/image/{}.png".format(str(count))
                return file_name
            count += 1
        return None


class MoDu:
    url = "https://www.cnmods.net/index/moduleListPage.do?moduleAge=&occurrencePlace=&duration=" \
            "&amount=&original=&releaseDateAsc=&moduleVersion=&freeLevel=&structure=&title={}" \
            "&page=1&pageSize=12&moduleType="
    key_url = "https://www.cnmods.net/#/moduleDetail/index?keyId={}"

    @classmethod
    async def _modu_search(cls, word: str) -> list:
        key = quote(word.replace(".md", "").replace("。md", "").strip())
        async with aiohttp.request('GET', cls.url.format(key)) as res:
            re = await res.text()
        # re = requests.get(cls.url.format(key)).text
        list_ = json.loads(re)["data"]["list"]
        return list_

    @classmethod
    def _modu_handler(cls, mozu: list) -> str:
        if not mozu:
            return "无结果"
        title = []
        urls = []
        for i in mozu:
            title.append(i['title'])
            urls.append(cls.key_url.format(i["keyId"]))
        mozu_len = len(title)
        out_msg = ""
        for i in range(mozu_len):
            out_msg += "{} : {}\n".format(title[i], urls[i])
        return out_msg

    @classmethod
    def _testmd(cls, mozu):
        urls = ""
        for i in mozu:
            urls += i["url"] + "\n"
        return urls

    @classmethod
    async def mozu_test(cls, word):
        return cls._testmd(await cls._modu_search(word))

    @classmethod
    async def mozu(cls, word: str) -> str:
        return cls._modu_handler(await cls._modu_search(word))


class SauceNAOSearch:
    _api = "e2be8c5c03a9396ee72c5ffcbcf975c5f3c35203"
    _sn = SN(api_key=_api)

    @classmethod
    def search_from_url(cls, url: str) -> list:
        try:
            res = cls._sn.from_url(url)
        except:
            return [Plain("请求出错了...")]
        else:
            out_msg = []
            num = 2
            if len(res):
                for i in res:
                    if num <= 0:
                        break
                    num -= 1
                    if len(i.urls):
                        out_msg.append(Plain("相似度：" + str(i.similarity) + "%:\n"))
                        lim = 2
                        for n in i.urls:
                            if lim <= 0:
                                break
                            lim -= 1
                            out_msg.append(Plain(n + "\n"))
            else:
                out_msg.append(Plain("QAQ找不到结果..."))
            if len(out_msg) == 0:
                return [Plain("QAQ找不到结果...")]
            return out_msg


class SuKeBeNyaa:
    _url = "https://sukebei.nyaa.si/?f=0&c=0_0&q={}&o=desc&s=seeders"
    _params = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4346.0 Safari/537.36 Edg/89.0.731.0",
    }

    @classmethod
    async def get_res(cls, keyword: str, group: bool = False) -> list:
        try:
            async with aiohttp.request('GET', cls._url.format(keyword), params=cls._params) as res:
                html = await res.text()
            # html = requests.get(cls._url.format(keyword), params=cls._params)
        except:
            return [Plain('QAQ出问题了...')]
        else:
            # html.encoding = html.apparent_encoding
            soup = bs(html, 'html.parser')
            if isinstance(soup.find(name='h3'), Tag):
                return [Plain('QAQ没有结果...')]
            all_ = soup.find(name='tbody').children
            num = 0
            out_msg = []
            for i in all_:
                if num >= 5:
                    break
                if isinstance(i, Tag):
                    t, m, num = cls._tag_handler(i, num, group)
                    out_msg.append(Plain(t + "\n" + m + "\n"))
                else:
                    pass
            return out_msg

    @classmethod
    def _tag_handler(cls, i: Tag, num: int, group: bool = False):
        all_ = i.find_all(name="td")
        title = all_[1].a.attrs['title'].strip()
        if len(title) > 10 and group is True:
            title = title[:10] + "...."
        main_url = "https://sukebei.nyaa.si/"
        magnet_all = all_[2].find_all(name="a")
        if len(magnet_all) < 2:
            magnet = magnet_all[0].attrs['href'].strip()
            num += 3
        else:
            magnet = main_url + magnet_all[0].attrs['href'].strip()
            num += 1
        return title, magnet, num


class WhatAnime:
    _main_url = 'https://trace.moe/api/search?url='
    _connector = ProxyConnector(
        proxy_type=ProxyType.SOCKS5,
        host='192.168.0.60',
        port=2089,
    )

    @classmethod
    async def search_anime(cls, url_str: str) -> List[Plain]:
        url_string = cls._main_url + url_str
        try:
            async with aiohttp.request('GET', url_string, connector=cls._connector) as res:
                json_data = await res.json()
        except BaseException as e:
            print(e)
            return [Plain('QAQ似乎发生了什么错误')]
        else:
            most_similar = json_data['docs']
            if most_similar:
                res = cls._most_similar_handler(most_similar[0])
                return res

    @classmethod
    def _most_similar_handler(cls, ms: dict) -> List[Plain]:
        msg_none = "None"
        title = ms['anime']
        if not title:
            title = msg_none
        episode = ms['episode']
        if not episode:
            episode = msg_none
        else:
            episode = str(episode)
        similarity = ms['similarity']
        if not similarity:
            similarity = msg_none
        else:
            similarity = "%.2f%%" % (similarity * 100)
        return [Plain('标题：' + title + '\n'), Plain('图片所在集数：' + episode + '\n'), Plain('相似度：' + similarity + '\n')]

if __name__ == '__main__':
    m = WhatAnime
    url = "https://ss1.baidu.com/9vo3dSag_xI4khGko9WTAnF6hhy/zhidao/pic/item/b58f8c5494eef01febefee31e1fe9925bd317d4f.jpg"

    print(m.search_anime(url).send(None))

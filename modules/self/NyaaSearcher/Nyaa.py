import time
from time import perf_counter

from feedparser import parse
from graia.ariadne.message.chain import MessageChain

from utils.func_retry import aretry
from utils.msgtool import make_forward_msg
from utils.session import Session


class Nyaa:
    url = "https://sukebei.nyaa.si/?page=rss&q={}&c=0_0&f=0"

    @classmethod
    @aretry()
    async def _fetch(cls, key_word: str) -> list[dict]:
        async with Session.proxy_session.get(cls.url.format(key_word)) as res:
            data = await res.text(encoding="utf-8")
        return parse(data).get("entries", [])

    @classmethod
    async def run(cls, key_word: str) -> MessageChain:
        start_time = perf_counter()
        info_list = await cls._fetch(key_word)
        if not info_list:
            return MessageChain("结果为空哦~😥")
        node_list = []
        limit = 10
        for i in info_list:
            if limit <= 0:
                break
            node_list.append(
                MessageChain(
                    f"标题: {i['title']}"
                    f"\ntorrent文件下载数: {i['nyaa_downloads']}"
                    f"\n分类: {i['nyaa_category']}"
                    f"\n正在下载的主机数: {i['nyaa_leechers']}"
                    f"\n已完成下载的主机数: {i['nyaa_seeders']}"
                    f"\n资源大小: {i['nyaa_size']}"
                    f"\n发布时间: {time.strftime('%Y-%m-%d %H:%M:%S',i['published_parsed'])}"
                    f"\ntorrent链接: {i['link']}"
                    f"\n详情: {i['id']}"
                    f"\nmagnet:?xt=urn:btih:{i['nyaa_infohash'].strip()}"
                ),
            )
            limit -= 1
        node_list.insert(
            0,
            MessageChain("提示！过于久远和冷门的torrent基本无法保证流畅下载😢"),
        )

        node_list.insert(
            0,
            MessageChain(f"已完成搜索🥰，共耗时{'%.3f' % (perf_counter()-start_time)}s"),
        )

        return MessageChain([make_forward_msg(node_list)])

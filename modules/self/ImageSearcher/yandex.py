from dataclasses import dataclass
from typing import Any

from lxml import etree
from PicImageSearch.network import HandOver

from utils.func_retry import aretry


@dataclass
class YandexItem:
    url: str
    thumbnail: str
    title: str


@dataclass
class YandexRespone:
    status_code: int
    raw: list[YandexItem]


class Yandex(HandOver):
    _url = "https://yandex.com/images/search?rpt=imageview&url="
    _request = (
        '&request={"blocks":[{"block":"extra-content","params":{},"version":2},'
        '{"block":"i-global__params:ajax","params":{},"version":2},{"block":"cbir-intent__image-link","params":{},"version":2},'
        '{"block":"content_type_search-by-image","params":{},"version":2},{"block":"serp-controller","params":{},"version":2},'
        '{"block":"cookies_ajax","params":{},"version":2},{"block":"advanced-search-block","params":{},"version":2}]}'
    )

    def __init__(self, **request_kwargs: Any):
        super().__init__(**request_kwargs)

    @aretry(2)
    async def search(self, url: str) -> YandexRespone:
        text, _, code = await self.get(self._url + url + self._request)
        items = etree.HTML(text).xpath("//li[@class='CbirSites-Item']")[0]
        return YandexRespone(
            status_code=code,
            raw=[
                YandexItem(url=data[0], thumbnail=data[1], title=data[2])
                for data in list(
                    zip(
                        items.xpath("//div[@class='CbirSites-ItemTitle']/a/@href"),
                        items.xpath("//div[@class='CbirSites-ItemThumb']/a/@href"),
                        items.xpath("//div[@class='CbirSites-ItemTitle']/a/text()"),
                    )
                )
            ],
        )

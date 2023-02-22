from dataclasses import dataclass
from datetime import datetime, timedelta

from graia.ariadne.entry import Image, MessageChain, Plain

from utils.func_retry import aretry
from utils.session import Session
from utils.t2i import md2img

_API = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale=zh-CN&country=CN&allowCountries=CN"


@dataclass
class Game:
    title: str
    description: str
    img_url: str
    url: str
    start_date: datetime
    end_date: datetime
    is_now: bool


@aretry()
async def _fetch() -> dict:
    async with Session.session.get(_API) as res:
        return await res.json()


def _parse(json: dict) -> list[Game]:
    game_list = []
    for element in json["data"]["Catalog"]["searchStore"]["elements"]:
        if not element["promotions"]:
            continue
        if element["promotions"]["promotionalOffers"]:
            time_element = element["promotions"]["promotionalOffers"][0]
            is_now = True
        else:
            time_element = element["promotions"]["upcomingPromotionalOffers"][0]
            is_now = False
        start_date = datetime.strptime(
            time_element["promotionalOffers"][0]["startDate"], "%Y-%m-%dT%H:%M:%S.000Z"
        ) + timedelta(hours=8)
        end_date = datetime.strptime(
            time_element["promotionalOffers"][0]["endDate"], "%Y-%m-%dT%H:%M:%S.000Z"
        ) + timedelta(hours=8)
        game_list.append(
            Game(
                title=element["title"],
                description=element["description"],
                img_url=element["keyImages"][0]["url"],
                url=f"https://store.epicgames.com/zh-CN/p/{element['offerMappings'][0]['pageSlug']}",
                start_date=start_date,
                end_date=end_date,
                is_now=is_now,
            )
        )
    return game_list


def _to_md(game_list: list[Game]) -> str:
    md = ""
    for game in game_list:
        # 标题居中
        md += f"<div align=center><h1>{game.title}</h1></div>\n\n"
        # 图片居中
        md += f"<div align=center><img src='{game.img_url}'/></div>\n\n"
        if game.is_now:
            md += f"**免费时间：{game.start_date}到{game.end_date}**\n\n"
        else:
            md += f"**开始免费时间：{game.start_date}**\n\n"
        md += f"{game.description}\n\n"
    return md


async def get_msg() -> MessageChain:
    json = await _fetch()
    game_list = _parse(json)
    img = await md2img(_to_md(game_list))
    info = "\n".join([f"{i.title}: {i.url}" for i in game_list if i.is_now])
    return MessageChain(
        [Plain("Epic免费游戏\n"), Image(data_bytes=img), Plain(f"\n{info}")]
    )

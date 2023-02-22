import asyncio
from asyncio import to_thread
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from time import perf_counter
from urllib import parse

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image as aImage
from graia.ariadne.message.element import Plain
from loguru import logger
from PIL import Image, ImageDraw, ImageFont

from utils.msgtool import make_forward_msg
from utils.session import Session


class TraceMoe:
    is_process: bool = False
    url_trace = "https://api.trace.moe/search?cutBorders&url={}"
    url_anilist = "https://trace.moe/anilist/"
    is_nfsw: bool = False
    anilist_query = {
        "query": "query ($ids: [Int]) {\n            "
        "Page(page: 1, perPage: 50) {\n              "
        "media(id_in: $ids, type: ANIME) {\n                "
        "id\n                title {\n                  "
        "native\n                  romaji\n                  "
        "english\n                }\n                "
        "type\n                format\n                "
        "status\n                startDate {\n                  "
        "year\n                  month\n                  "
        "day\n                }\n                "
        "endDate {\n                  year\n                  "
        "month\n                  day\n                }\n                "
        "season\n                episodes\n                "
        "duration\n                source\n                "
        "coverImage {\n                  large\n                  "
        "medium\n                }\n                bannerImage\n                "
        "genres\n                synonyms\n                studios {\n                  "
        "edges {\n                    isMain\n                    node {\n                      "
        "id\n                      name\n                      siteUrl\n                    "
        "}\n                  }\n                }\n                isAdult\n                "
        "externalLinks {\n                  id\n                  url\n                  "
        "site\n                }\n                siteUrl\n              }\n            "
        "}\n          }\n          ",
        "variables": {"ids": []},
    }
    limit = 3

    @classmethod
    @contextmanager
    def _process(cls):
        cls.is_process = True
        try:
            yield
        finally:
            cls.is_process = False

    @classmethod
    async def fetch(cls, url: str) -> dict:
        url = cls.url_trace.format(parse.quote_plus(url))
        async with Session.proxy_session.get(url) as res:
            return await res.json()

    @classmethod
    async def fetch_img(cls, img_url: str) -> bytes:
        async with Session.proxy_session.get(img_url) as res:
            return await res.read()

    @classmethod
    async def fetch_anilist(cls, data: dict) -> dict:
        async with Session.proxy_session.post(cls.url_anilist, json=data) as res:
            return await res.json()

    @classmethod
    def parse_data(cls, trace_data: dict, anilist_data: dict) -> list[dict]:
        data_list = []
        num = 0
        for i in trace_data["result"]:
            if num == cls.limit:
                break
            id_ = i["anilist"]
            for n in anilist_data["data"]["Page"]["media"]:
                if n["id"] == id_:
                    i.update({"anilist": n})
                    data_list.append(i)
                    num += 1
                    break
        return data_list

    @classmethod
    async def run(cls, image_url: str):
        with cls._process():
            start = perf_counter()
            td = await cls.fetch(image_url)
            ids = list({i["anilist"] for i in td["result"]})
            cls.anilist_query["variables"].update({"ids": ids})
            ad = await cls.fetch_anilist(cls.anilist_query)
            data = cls.parse_data(td, ad)

            external_links_str = []
            cover_task = []
            search_task = []
            for i in range(cls.limit):
                cover_task.append(
                    cls.fetch_img(data[i]["anilist"]["coverImage"]["large"])
                )
                search_task.append(cls.fetch_img(data[i]["image"]))
                link_str = "".join(
                    n["site"] + ":" + n["url"] + "\n"
                    for n in data[i]["anilist"]["externalLinks"]
                )
                external_links_str.append("\n资源链接：\n" + link_str if link_str else "")
            cover_search_image_bytes = await asyncio.gather(*cover_task, *search_task)
            cover_image_bytes = cover_search_image_bytes[
                : len(cover_search_image_bytes) // 2
            ]
            search_image_byets = cover_search_image_bytes[
                len(cover_search_image_bytes) // 2 :
            ]
            message = []
            res_len = len(cover_image_bytes)
            imgs = await asyncio.gather(
                *[
                    to_thread(
                        draw_tracemoe,
                        data[i],
                        cover_image_bytes[i],
                        search_image_byets[i],
                    )
                    for i in range(res_len)
                ]
            )
            message = [
                MessageChain(
                    [
                        aImage(data_bytes=imgs[i]),
                        Plain(external_links_str[i] or "\n无资源链接"),
                    ]
                )
                for i in range(res_len)
            ]

            if len(message) > 1:
                message.insert(1, MessageChain("以下为其他可能结果, 请自行查看"))
            message.insert(
                0,
                MessageChain(f"搜番结果如下, 共耗时{'%.3f' % (perf_counter() - start)}s"),
            )
            return MessageChain(make_forward_msg(message))


FONT_PATH = Path("resources/fonts")


def sec_to_minsec(sec):
    minutes, seconds = divmod(int(sec), 60)
    return f"{minutes:02d}:{seconds:02d}"


def draw_tracemoe(search_data, cover_bytes: bytes, search_byetes: bytes):
    title_font = ImageFont.truetype(
        str(FONT_PATH.joinpath("sarasa-mono-sc-semibold.ttf")), 28
    )
    subtitle_font = ImageFont.truetype(
        str(FONT_PATH.joinpath("sarasa-mono-sc-semibold.ttf")), 18
    )
    body_font = ImageFont.truetype(
        str(FONT_PATH.joinpath("sarasa-mono-sc-regular.ttf")), 22
    )

    bg_x = 900

    # 标题
    title_img = Image.new("RGB", (bg_x, 100), "#f9bcdd")  # type: ignore
    draw = ImageDraw.Draw(title_img)
    draw.text((17, 15), search_data["anilist"]["title"]["native"], "white", title_font)
    draw.text(
        (17, 55), search_data["anilist"]["title"]["romaji"], "white", subtitle_font
    )

    cover_img = _extracted_from_draw_tracemoe_22(cover_bytes, 400)
    # 剧集信息
    start_date = "-".join(
        [
            str(search_data["anilist"]["startDate"][x])
            for x in search_data["anilist"]["startDate"]
        ]
    )
    end_date = "-".join(
        [
            str(search_data["anilist"]["endDate"][x])
            for x in search_data["anilist"]["endDate"]
        ]
    )
    airing = f"{start_date} 至 {end_date}"
    title_dict = search_data["anilist"].get("title", {})
    trans_name = (
        (f'{title_dict.get("chinese", " ")}\n' f'{title_dict.get("english", " ")}')
        if title_dict
        else ""
    )
    info = (
        f"{search_data['anilist']['episodes']} episodes "
        f"{search_data['anilist']['duration']}-minute "
        f"{search_data['anilist']['format']} "
        f"{search_data['anilist']['type']}\n"
        f"播出于 {airing}"
    )
    info_img = Image.new("RGB", (bg_x, 300), "white")  # type: ignore
    draw = ImageDraw.Draw(info_img)
    draw.text((100, 20), info, (50, 50, 50), body_font)
    draw.line(((55, 22), (55, 73)), (100, 100, 100), 8)
    draw.text((45, 110), "译名", (50, 50, 50), title_font)
    draw.text((120, 103), trans_name, (50, 50, 50), body_font)

    # 识别信息
    search_text = (
        f"出自第 {str(search_data['episode'])} 集\n"
        f"{sec_to_minsec(search_data['from'])} 至 {sec_to_minsec(search_data['to'])}\n"
        f"相似度：{'%.2f%%' % (search_data['similarity'] * 100)}"
    )
    search_img = Image.new("RGB", (bg_x, 220), "white")  # type: ignore
    draw = ImageDraw.Draw(search_img)
    screenshot = _extracted_from_draw_tracemoe_22(search_byetes, 220)
    search_img.paste(screenshot, (0, 0))
    draw.text((430, 50), search_text, (20, 20, 20), body_font, spacing=12)

    # 输出
    bg = Image.new("RGB", (bg_x, 500), "#d5a4cf")  # type: ignore
    bg.paste(title_img, (0, 0))
    bg.paste(info_img, (0, 100))
    bg.paste(search_img, (0, 280))
    # if not search_data["anilist"]["isAdult"]:
    bg.paste(cover_img, (bg_x - cover_img.size[0], 100))
    bio = BytesIO()
    bg.save(bio, "JPEG")
    return bio.getvalue()


# TODO Rename this here and in `draw_tracemoe`
def _extracted_from_draw_tracemoe_22(arg0, arg1):
    result = Image.open(BytesIO(arg0))
    coverx, covery = result.size
    if covery < arg1:
        ratio = covery / coverx
        result = result.resize((int(arg1 / ratio), arg1))
    else:
        result.thumbnail((1000, arg1))

    return result

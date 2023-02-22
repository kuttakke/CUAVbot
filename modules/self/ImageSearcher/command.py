from graia.ariadne.entry import At, Image
from graia.ariadne.message.parser.twilight import (
    ElementMatch,
    RegexMatch,
    SpacePolicy,
    Twilight,
)


def _get_twilight(keyword):
    return Twilight(
        [
            ElementMatch(At, optional=True).space(SpacePolicy.PRESERVE),
            RegexMatch(keyword).space(SpacePolicy.PRESERVE),
            ElementMatch(Image, optional=True).space(SpacePolicy.PRESERVE) @ "img",
        ]
    )


class Command:
    Default = _get_twilight(r"[.。!！]((谷歌)|(百度)|(二次元))?搜图\s?")
    Waifu = _get_twilight("[.。!！]二次元搜图")
    Google = _get_twilight("[.。!！]((谷歌)|(百度))搜图")
    Baidu = _get_twilight("[.。!！]((谷歌)|(百度))搜图")
    Anime = _get_twilight("[.。!！]搜番")

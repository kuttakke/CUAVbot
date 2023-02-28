from graia.ariadne.entry import RegexMatch, Twilight, WildcardMatch
from graia.ariadne.message.parser.twilight import SpacePolicy


class Command:
    DynamicSub = Twilight(
        [
            RegexMatch(r"[.。!！]订阅").space(SpacePolicy.FORCE),
            WildcardMatch(greed=False) @ "uid",
        ]
    )
    DynamicUnSub = Twilight(
        [
            RegexMatch(r"[.。!！]取消订阅").space(SpacePolicy.FORCE),
            WildcardMatch(greed=False) @ "uid",
        ]
    )
    SubList = Twilight(
        [
            RegexMatch(r"[.。!！]订阅列表"),
        ]
    )

from graia.ariadne.message.element import At
from graia.ariadne.message.parser.twilight import (
    ElementMatch,
    RegexMatch,
    SpacePolicy,
    Twilight,
    WildcardMatch,
)


class Command:
    Time = Twilight(
        [
            ElementMatch(At, optional=True).space(SpacePolicy.PRESERVE),
            RegexMatch(r"[.。!！]闹钟").space(SpacePolicy.PRESERVE),
            WildcardMatch(optional=False) @ "cmd",
        ]
    )

    Remove = Twilight([RegexMatch(r"[.。!！]((取消闹钟)|(删除闹钟))(\s\d+)?") @ "cmd"])

    Check = Twilight([RegexMatch(r"[.。!！]((查看闹钟)|(显示闹钟))(\s\d+)?")])

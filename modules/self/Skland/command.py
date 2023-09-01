from graia.ariadne.message.parser.twilight import (
    RegexMatch,
    SpacePolicy,
    Twilight,
    WildcardMatch,
)


class Command:
    BindingPlayer = Twilight(
        RegexMatch(r"[.。！!](森空岛绑定|绑定森空岛)").space(SpacePolicy.PRESERVE),
        WildcardMatch(greed=False, optional=True).space(SpacePolicy.PRESERVE) @ "cerd",
    )
    Sign = Twilight(
        RegexMatch(r"[.。！!]((森空岛签到)|(签到森空岛))"),
    )
    ShowPlayerInfo = Twilight(
        RegexMatch(r"[.。！!]((森空岛信息)|(查询森空岛)|(森空岛查询)|(森空岛数据))"),
    )
    UnBind = Twilight(
        RegexMatch(r"[.。！!]((森空岛解绑)|(解绑森空岛)|(森空岛删除)|(删除森空岛))"),
    )
    TimerSign = "1 0 * * *"

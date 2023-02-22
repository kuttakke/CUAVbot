from graia.ariadne.message.parser.twilight import (
    ArgumentMatch,
    FullMatch,
    MatchResult,
    RegexMatch,
    SpacePolicy,
    Twilight,
    WildcardMatch,
)


class Command:
    AddUser = Twilight(
        [
            FullMatch("绑定原神").space(SpacePolicy.PRESERVE),
            WildcardMatch(optional=True) @ "cookies",
        ]
    )
    RemoveUser = Twilight([FullMatch("解绑原神"), ArgumentMatch("-u", "--uid") @ "uid"])
    ForceRemoveUser = Twilight([FullMatch("强制解绑原神")])
    DeleteUser = Twilight(
        [FullMatch("删除原神"), ArgumentMatch("-i", "--id", optional=False) @ "id"]
    )
    UpdateUser = Twilight(
        [FullMatch("更新原神").space(SpacePolicy.PRESERVE), WildcardMatch() @ "cookies"]
    )
    TimeSign = "11 0 * * *"
    TimeMarkSign = "0 0 * * *"
    Sign = Twilight([FullMatch("签到原神")])
    DailyNote = Twilight([FullMatch("原神每日")])
    SwitchDailyNote = Twilight([RegexMatch(r"(关闭|开启)树脂提醒") @ "cmd"])
    SwitchDailySign = Twilight([RegexMatch(r"(关闭|开启)每日签到") @ "cmd"])
    SwitchGlobalSign = Twilight([RegexMatch(r"(关闭|开启)全局签到") @ "cmd"])
    TimeResetResinEveryHour = 24

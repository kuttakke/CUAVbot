import re

from graia.ariadne.message.parser.twilight import (
    ArgumentMatch,
    FullMatch,
    MatchResult,
    RegexMatch,
    Twilight,
)


class Command:
    RunUpdate = Twilight(
        [
            RegexMatch(r"((up)|(更新))((pixiv)|(pix)|(p站))").flags(
                re.RegexFlag(re.IGNORECASE)
            )
        ]
    )
    AddOrRemoveBlockTag = Twilight([RegexMatch(r"^(解除)?屏蔽标签[\s\S]+") @ "tag"])
    ActivateTrigger = Twilight([RegexMatch(r"((关闭)|(开启))更新") @ "trigger"])
    GlobalActivateTrigger = Twilight([RegexMatch(r"((关闭)|(开启))全局更新") @ "trigger"])
    DeleteUser = Twilight([FullMatch(r"删除pix账号")])
    Login = Twilight(
        [
            RegexMatch(r"^pix登录").flags(re.RegexFlag(re.IGNORECASE)),
            ArgumentMatch("-u", "--user") @ "user",
            ArgumentMatch("-p", "--password") @ "password",
            ArgumentMatch("-t", "--token") @ "token",
        ]
    )
    Status = Twilight([FullMatch("pix账号状态")])
    Nsfw = Twilight(
        [RegexMatch(r"((关闭)|(开启))r18").flags(re.RegexFlag(re.IGNORECASE)) @ "nsfw"]
    )
    PushUpdate = Twilight([FullMatch("push pixup")])
    AllUserStatus = Twilight([FullMatch("pix状态")])
    TimeStatus = "0 0 * * *"
    TimeUpdateEveryMinutes = 90

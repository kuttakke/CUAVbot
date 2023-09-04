import re

from graia.ariadne.message.parser.twilight import (
    RegexMatch,
    SpacePolicy,
    Twilight,
    WildcardMatch,
)


class Command:
    Ask = Twilight(
        [
            RegexMatch(r"(.*)(?<=^[.。！!])(chat|ai|chatgpt|openai)")
            .space(SpacePolicy.PRESERVE)
            .flags(re.RegexFlag.IGNORECASE),
            # WildcardMatch(greed=True) @ "ask",
            RegexMatch(r"[\s\S]*") @ "ask",
        ]
    )

    RoleList = Twilight(
        RegexMatch(r"[.。！!](role list|角色列表)").flags(re.RegexFlag.IGNORECASE),
    )

    SetRole = Twilight(
        RegexMatch(r"[.。！!](设置角色|set role)")
        .space(SpacePolicy.PRESERVE)
        .flags(re.RegexFlag.IGNORECASE),
        WildcardMatch(greed=False) @ "role",
    )

    ResetChat = Twilight(
        RegexMatch(r"[.。！!](重置上下文|reset ai|reset chat|reset chatgpt|reset openai)")
        .space(SpacePolicy.PRESERVE)
        .flags(re.RegexFlag.IGNORECASE),
    )

    AddCustomRole = Twilight(
        RegexMatch(r"[.。！!](添加自定义角色|添加自定义prompt|角色自定义|自定义ai)").flags(
            re.RegexFlag.IGNORECASE
        ),
    )

    ShowCustomRole = Twilight(
        RegexMatch(r"[.。！!](查看自定义角色|查看自定义prompt|查看角色自定义|查看自定义ai|查看角色列表|角色列表)").flags(
            re.RegexFlag.IGNORECASE
        ),
    )

    RemoveCustomRole = Twilight(
        RegexMatch(r"[.。！!](删除自定义角色|删除自定义prompt|删除角色自定义|删除自定义ai)")
        .space(SpacePolicy.FORCE)
        .flags(re.RegexFlag.IGNORECASE),
        WildcardMatch(greed=False) @ "role",
    )

    Usage = Twilight(
        RegexMatch(r"[.。！!](usage|使用情况)").flags(re.RegexFlag.IGNORECASE),
    )

    TotalUsage = Twilight(RegexMatch(r"[.。！!](total usage|总使用情况)"))

    TimeReset = "0 4 * * *"

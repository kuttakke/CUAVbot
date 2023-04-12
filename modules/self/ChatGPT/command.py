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
            RegexMatch(r"[.。！!](chat|ai|chatgpt|openai)")
            .space(SpacePolicy.PRESERVE)
            .flags(re.RegexFlag.IGNORECASE),
            WildcardMatch(greed=False) @ "ask",
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

    Usage = Twilight(
        RegexMatch(r"[.。！!](usage|使用情况)").flags(re.RegexFlag.IGNORECASE),
    )

    TotalUsage = Twilight(RegexMatch(r"[.。！!](total usage|总使用情况)"))

    TimeReset = "0 4 * * *"

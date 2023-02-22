from graia.ariadne.message.element import At
from graia.ariadne.message.parser.twilight import (
    ElementMatch,
    RegexMatch,
    SpacePolicy,
    Twilight,
    WildcardMatch,
)


class Command:
    BanUnban = Twilight(
        [
            RegexMatch(r"[.|。|!|！](un)?ban").space(SpacePolicy.FORCE) @ "cmd",
            WildcardMatch(greed=False).space(SpacePolicy.PRESERVE) @ "module",
            ElementMatch(At, optional=True) @ "at",
        ]
    )

    InstallUninstall = Twilight(
        [
            RegexMatch(r"[.|。|!|！](un)?install").space(SpacePolicy.FORCE) @ "cmd",
            WildcardMatch(greed=False).space(SpacePolicy.PRESERVE) @ "module",
        ]
    )

    Reload = Twilight(
        [
            RegexMatch(r"[.|。|!|！]reload").space(SpacePolicy.FORCE),
            WildcardMatch(greed=False).space(SpacePolicy.PRESERVE) @ "module",
        ]
    )

    Menu = Twilight([RegexMatch(r"[.|。|!|！](菜单|menu)")])

    Help = Twilight(
        [
            RegexMatch(r"[.|。|!|！](用法|help)").space(SpacePolicy.FORCE),
            WildcardMatch(greed=False) @ "module",
        ]
    )

    Restart = Twilight([RegexMatch(r"[.|。|!|！](restart|重启)")])

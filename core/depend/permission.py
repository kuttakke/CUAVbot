from graia.ariadne.app import Ariadne
from graia.ariadne.model import Friend, Group, Member
from graia.broadcast import ExecutionStop
from graia.broadcast.builtin.decorators import Depend

from config import settings


class Permission:
    _MEMBER_PERM_LV_MAP: dict[str, int] = {
        "MEMBER": 1,
        "ADMINISTRATOR": 2,
        "OWNER": 3,
    }

    _MEMBER_PERM_REPR_MAP: dict[str, str] = {
        "MEMBER": "<普通成员>",
        "ADMINISTRATOR": "<管理员>",
        "OWNER": "<群主>",
    }

    @classmethod
    def required(cls, level: int = 2, notice: bool = False) -> Depend:
        """限制权限

        Args:
            level (int, optional): 1-普通群员 2-管理员 3-群主. Defaults to 2.
            notice (bool, optional): _description_. Defaults to False.

        Returns:
            Depend: _description_
        """

        async def wrapper(app: Ariadne, group: Group, member: Member):
            if cls._MEMBER_PERM_LV_MAP[member.permission.value] < level:
                if notice:
                    await app.send_group_message(group, "权限不足😢")
                raise ExecutionStop

        return Depend(wrapper)

    @classmethod
    def r_debug(cls) -> Depend:
        def wrapper(group: Group, member: Member):
            if (
                group.id != settings.mirai.debug_group
                and member.id != settings.mirai.master
            ):
                raise ExecutionStop

        return Depend(wrapper)

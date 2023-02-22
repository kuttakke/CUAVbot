from graia.ariadne.event.message import FriendMessage, GroupMessage, MessageEvent
from graia.ariadne.model import Friend, Group, Member
from graia.broadcast import ExecutionStop
from graia.broadcast.builtin.decorators import Depend

from core.control import Controller


class BlackList:
    @classmethod
    def require(cls, module_name: str) -> Depend:
        async def wrapper(event: MessageEvent):
            if isinstance(event, GroupMessage):
                if any(
                    [
                        await Controller.is_block(module_name, event.sender.group.id),
                        await Controller.is_block(
                            module_name, event.sender.group.id, event.sender.id
                        ),
                    ]
                ):
                    raise ExecutionStop
            elif isinstance(event, FriendMessage):
                if await Controller.is_block_friend(module_name, event.sender.id):
                    raise ExecutionStop

        return Depend(wrapper)

from pathlib import Path

from graia.ariadne.entry import FriendMessage, GroupMessage, MessageChain, Source
from graia.ariadne.event.message import MessageEvent
from graiax.shortcut.saya import listen

from core.control import Controller
from core.entity import ChatFriendLog, ChatGroupLog, Modules
from utils.tool import to_module_file_name

module_name = "消息记录器"

module = Modules(
    name=module_name,
    author="Kutake",
    description="群&好友消息记录器",
    file_name=to_module_file_name(Path(__file__)),
)

channel = Controller.module_register(module)


@listen(GroupMessage, FriendMessage)
async def msg_log(event: MessageEvent, msg: MessageChain, source: Source):
    if isinstance(event, GroupMessage):
        await Controller.db.add(
            ChatGroupLog,
            values={
                "group_id": event.sender.group.id,
                "member_id": event.sender.id,
                "message_id": source.id,
                "as_persistent_string": msg.as_persistent_string(),
                "create_time": source.time,
            },
        )
        return
    await Controller.db.add(
        ChatFriendLog,
        values={
            "friend_id": event.sender.id,
            "message_id": source.id,
            "as_persistent_string": msg.as_persistent_string(),
            "create_time": source.time,
        },
    )

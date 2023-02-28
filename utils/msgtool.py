""" 关于sendMessage的工具方法 """

from datetime import datetime
from typing import Sequence

from graia.ariadne.entry import (
    Ariadne,
    At,
    Element,
    Forward,
    ForwardNode,
    Friend,
    Group,
    Image,
    Member,
    MessageChain,
    Plain,
    Source,
)
from graia.ariadne.event.message import MessageEvent
from graia.ariadne.exception import RemoteException, UnknownTarget
from graia.ariadne.message.element import DisplayStrategy

from config import settings
from core.control import Controller
from core.entity import BlockListGroup
from utils import aretry

__all__ = (
    "get_ariadne",
    "send_group",
    "send_friend",
    "send_debug",
    "make_forward_msg",
    "send_message_by_black_list",
)


def get_ariadne() -> Ariadne:
    """获取Ariadne实例"""
    return Ariadne.current()


async def _is_source_exists(source: int | Source) -> bool:
    """检查source消息是否存在"""
    if isinstance(source, Source):
        source = source.id
    try:
        await get_ariadne().get_message_from_id(source)
        return True
    except UnknownTarget:
        return False


def _make_msg(
    msg: MessageChain | str | bytes, at: Member | int | None = None
) -> MessageChain:
    """生成消息实例"""
    if not isinstance(msg, MessageChain):
        msg = MessageChain(
            [Image(data_bytes=msg) if isinstance(msg, bytes) else Plain(msg)]
        )
    if at:
        msg = MessageChain([At(at)]).extend(msg)
    return msg


async def send_group(
    target: int | Group,
    msg: MessageChain | str | bytes,
    quote: int | Source | None = None,
    at: Member | int | None = None,
    is_quote_safe: bool = True,
):
    """
    发送群消息
    :param target: 群ID
    :param msg: 需要发送的 消息链 | 字符串 | 图片bytes
    :param quote: 需要回复的消息
    :param at: 传入时自动群员
    :param is_quote_safe: 需要回复的消息是否确定可以被找到
    :return: None
    """
    msg = _make_msg(msg, at)
    group = (
        target if isinstance(target, Group) else await get_ariadne().get_group(target)
    )
    assert group
    return await get_ariadne().send_group_message(
        target=group,
        message=msg,
        quote=quote
        if quote and (is_quote_safe or await _is_source_exists(quote))
        else None,
    )


async def send_debug(msg: MessageChain | str | bytes):
    """发送调试消息"""
    return await get_ariadne().send_group_message(
        target=settings.mirai.debug_group, message=_make_msg(msg)
    )


def make_forward_msg(msg: Sequence[str | bytes | MessageChain]) -> Forward:
    """生成转发消息

    Args:
        msg (list[str, bytes, MessageChain]): 需要转发的消息

    Returns:
        Forward: 转发消息
    """
    nodes = []
    preview = []
    for i in msg:
        msg_node = _make_msg(i)
        nodes.append(
            ForwardNode(
                target=settings.mirai.account,
                time=datetime.now(),
                message=msg_node,
                name=settings.mirai.bot_name,
            )
        )
        preview.append(f"{settings.mirai.bot_name}:{msg_node.display.strip()}")

    return Forward(
        node_list=nodes,
        display=DisplayStrategy(
            title="群聊的聊天记录",
            brief="[聊天记录]",
            source="聊天记录",
            preview=preview,
            summary=f"查看{len(msg)}条转发消息",
        ),
    )


async def send_friend(
    target: int | Friend,
    msg: MessageChain | str | bytes,
    quote: int | Source | None = None,
    is_quote_safe: bool = True,
):
    """
    发送群消息
    :param target: 群ID
    :param msg: 需要发送的 消息链 | 字符串 | 图片bytes
    :param quote: 需要回复的消息
    :param is_quote_safe: 需要回复的消息是否确定可以被找到
    :return: None
    """
    msg = _make_msg(msg)
    return await get_ariadne().send_friend_message(
        target=target,
        message=msg,
        quote=quote
        if quote and (is_quote_safe or await _is_source_exists(quote))
        else None,
    )


async def _get_block_id_list(module_name: str) -> list[int]:
    block_group_list = await Controller.db.select(
        BlockListGroup, [BlockListGroup.module == module_name]
    )
    return [i.group_id for i in block_group_list]


async def send_message_by_black_list(
    module_name: str, msg: MessageChain | list[MessageChain]
):
    """群发消息，排除黑名单群

    Args:
        module_name (str): 模组名称
        msg (MessageChain | list[list[Element]]): 消息
    """
    app = get_ariadne()
    block_group_id_list = await _get_block_id_list(module_name)
    for group in await app.get_group_list():
        if group.id in block_group_id_list:
            continue
        if isinstance(msg, list):
            for i in msg:
                await app.send_group_message(group.id, i)
        else:
            await app.send_group_message(group.id, msg)


@aretry(times=2, exceptions=(RemoteException,))
async def send_forward_msg_with_retry(target: MessageEvent, msg: MessageChain):
    """由于转发消息的192错误，需要重试

    Args:
        target (int | Friend | Group): 目标
        msg (MessageChain): 消息
    """
    return await get_ariadne().send_message(target=target, message=msg)

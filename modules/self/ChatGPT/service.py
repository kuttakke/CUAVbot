from sqlmodel import col, desc, func, select

from .entity import ChatLog, GroupConfig, db


async def insert_chat_log(chat_log: ChatLog):
    """插入聊天记录"""
    await db.add(ChatLog, values=chat_log.dict())


async def get_last_chat_log(group_id: int, user_id: int, prompt_title: str) -> ChatLog:
    """获取最后一条聊天记录"""
    stmt = (
        select(ChatLog)
        .where(
            col(ChatLog.group_id) == group_id,
            col(ChatLog.user_id) == user_id,
            col(ChatLog.system_prompt_title) == prompt_title,
        )
        .order_by(desc(ChatLog.created))
    )
    return await db.select_one(stmt)


async def get_group_config(group_id: int) -> GroupConfig:
    """获取群组配置"""
    stmt = select(GroupConfig).where(col(GroupConfig.group_id) == group_id)
    return await db.select_one(stmt)


async def change_group_config(config: GroupConfig):
    """更改群组配置"""
    await db.update(
        GroupConfig,
        config.dict(),
        [GroupConfig.group_id == config.group_id],
        or_create=True,
    )


async def count_chat_token(group_id: int, user_id: int):
    """统计消耗的token"""
    stmt_group = select(func.sum(ChatLog.token)).where(  # type: ignore
        col(ChatLog.group_id) == group_id
    )
    group_tokens = await db.execute(stmt_group)
    stmt_member = select(func.sum(ChatLog.token)).where(  # type: ignore
        col(ChatLog.group_id) == group_id,
        col(ChatLog.user_id) == user_id,
    )
    member_tokens = await db.execute(stmt_member)
    return (
        int(group_tokens.first() or 0),
        int(member_tokens.first() or 0),
    )  # type: ignore


async def count_total_chat_token():
    stmt = select(func.sum(ChatLog.token))  # type: ignore
    token = await db.execute(stmt)
    return int(token.first() or 0)  # type: ignore


async def get_chatted_group_ids() -> list[int]:
    """获取已经聊过天的群号"""
    stmt = select(ChatLog.group_id).distinct()
    return (await db.execute(stmt)).all()


# async def get_group_chat_log(group_id: int, limit: int) -> list[ChatGroupLog]:
#     return await Controller.get_last_chat_group_log(group_id, limit)

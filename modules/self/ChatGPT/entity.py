from sqlmodel import Field

from service.db import DataBase

db = DataBase(DataBase.make_sqlite_url(__file__))


class ChatLog(db.Model, table=True):
    """chatGPT聊天记录"""

    __tablename__ = "chat_log"  # type: ignore

    id: str = Field(primary_key=True)
    object: str = Field(index=True)
    created: int = Field()  # 时间戳
    conversation: str = Field()  # 对话上下文
    token: int = Field(index=True)  # 消耗的token
    group_id: int = Field(index=True)  # 群号
    user_id: int = Field(index=True)  # 用户号
    system_prompt_title: str = Field()  # 系统提示标题


class GroupConfig(db.Model, table=True):
    """群配置"""

    __tablename__ = "group_config"  # type: ignore
    group_id: int = Field(primary_key=True)
    role_id: int = Field()
    prompt_title: str = Field()
    default_conversation: str = Field()


class CustomRole(db.Model, table=True):
    """自定义角色"""

    __tablename__ = "custom_role"  # type: ignore
    __table_args__ = {"sqlite_autoincrement": True}

    id: int | None = Field(default=None, primary_key=True)
    group_id: int = Field()
    member_id: int = Field()
    role_name: str = Field()
    role_prompt: str = Field()
    default_reply: str = Field()


# class RandomConfig(db.Model, table=True):
#     """随机回复配置"""

#     __tablename__ = "random_config"  # type: ignore
#     group_id: int = Field(primary_key=True)
#     enable: bool = Field()


# class RandomResponseLog(db.Model, table=True):
#     """随机回复"""

#     __tablename__ = "random_response_log"  # type: ignore
#     id: str = Field(primary_key=True)
#     object: str = Field(index=True)
#     created: int = Field()  # 时间戳
#     conversation: str = Field()  # 对话上下文
#     token: int = Field(index=True)  # 消耗的token
#     group_id: int = Field(index=True)  # 群号

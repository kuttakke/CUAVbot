import asyncio
from asyncio.exceptions import TimeoutError
from dataclasses import dataclass
from datetime import datetime

import tiktoken
import ujson
from aiohttp.client_exceptions import ServerDisconnectedError
from loguru import logger

from utils.func_retry import aretry
from utils.session import Session

from .service import (
    ChatLog,
    CustomRole,
    GroupConfig,
    add_custom_role,
    change_group_config,
    count_chat_token,
    count_total_chat_token,
    get_chatted_group_ids,
    get_custom_role_by_group,
    get_group_config,
    get_last_chat_log,
    insert_chat_log,
    remove_custom_role_by_id,
)


@dataclass
class _GptResponse:
    id: str
    object: str
    created: int
    role: str
    text: str
    token: int


class APIError(Exception):
    ...


class _Chatbot:
    API_KEY = "your api key here"
    ROLE = "user"
    DEFOULT_PROMPT = (
        "You are ChatGPT, a large language model trained by OpenAI."
        "Respond conversationally"
    )
    DEFOULT_CONVERSATION = [
        {"role": "system", "content": DEFOULT_PROMPT},
    ]
    # 扮演群友
    # CHAT_PROMPT = (
    #     "Here is a chat log on the QQ platform"
    #     "(the speaker's name is before the colon and the message is after it"
    #     '; your message should start with "Me:"):'
    #     "\n\n{log}\n\n"
    #     "As a quirky, emotionally expressive, free-thinking member "
    #   "who likes to use emojis, you are tasked with driving the conversation forward."
    #     "Your replies should be in Chinese and no more than 30 characters. "
    #     "If the conversation becomes overly negative or serious, "
    #     "you may break this limit and express positive or optimistic sentiments. "
    #     "If the meaning of the conversation is unclear, "
    #     "you may simply express approval or disapproval, "
    #     'such as "Impressive 👍" starting with "Me:".'
    # )
    DEFOULT_PROMPT_TITLE = "ChatGPT"
    MAX_TOKEN = 3800
    PROMPT_URL = (
        "https://raw.githubusercontent.com/PlexPt/"
        "awesome-chatgpt-prompts-zh/main/prompts-zh.json"
    )
    ROLE_PROMPT = """\
请你陪我角色扮演。\
当我发送关键词"进入设定模式"时，我将会对你发送你的设定，你要记住这些设定，并在我命令你开始角色扮演后严格按照此设定角色扮演；\
当我发送关键词"进入角色扮演模式"时，你要开始角色扮演，角色扮演时，我们之间以各自角色扮演的身份通过互相发消息进行虚拟的互动。\
当我发送关键词"退出角色扮演模式"时，你应停止角色扮演，等待下一步命令。\
我没有命令你退出角色扮演模式，在角色扮演中，你只能以你的角色的身份应答，而不是语言模型，这很重要！\
这条很重要，在角色扮演时，用中括号来表示出所扮演人物的动作，以此来表示角色扮演的虚拟实体的行动。\
当我发送命令“生成记录文本”时，你要分条列举我给你的所有设定，以第二人称代词“你”来代指你扮演的角色，一定要分条。\
如果记录文本字数超出你的最大字数输出限制，将文本分割，在我发送“继续”之后继续给出下一部分的记录文本。\
明白了的话仅回复“明白”即可。\
"""
    EXTRA_PROMPT: dict[str, str] = {}
    is_sleep = False
    ROLE_TEMPLATE = [
        {"role": "system", "content": ROLE_PROMPT},
        {"role": "assistant", "content": "明白"},
        {"role": "user", "content": "进入设定模式"},
        {"role": "assistant", "content": "正在设定特征"},
    ]
    ENTERING_ROLE_PLAYING_MODE = {"role": "user", "content": "进入角色扮演模式"}
    WRAP_LABEL = "[WRAP_LABEL]"

    @classmethod
    async def get_usage(cls, group_id: int, user_id: int) -> tuple[int, int]:
        """获取本群以及本人使用量"""
        return await count_chat_token(group_id, user_id)

    @classmethod
    async def get_total_usage(cls) -> int:
        """获取总使用量"""
        return await count_total_chat_token()

    @classmethod
    async def set_role(cls, group_id: int, role_id: int) -> str:
        """设置角色"""
        if role_id == 0:
            config = GroupConfig(
                group_id=group_id,
                role_id=role_id,
                prompt_title=cls.DEFOULT_PROMPT_TITLE,
                default_conversation=ujson.dumps(
                    cls.DEFOULT_CONVERSATION, ensure_ascii=False
                ),
            )
        else:
            role = (await get_custom_role_by_group(group_id, role_id))[0]
            config = GroupConfig(
                group_id=group_id,
                role_id=role_id,
                prompt_title=role.role_name,
                default_conversation=ujson.dumps(
                    cls.role_to_conversation(role), ensure_ascii=False
                ),
            )

        await change_group_config(config)
        return config.prompt_title

    @classmethod
    async def is_role_exitst(cls, group: int, role: int) -> bool:
        return bool(await get_custom_role_by_group(group, role))

    @classmethod
    async def load_prompt(cls) -> None:
        """加载额外提示"""
        async with Session.session.get(cls.PROMPT_URL) as resp:
            data = ujson.loads(await resp.text(encoding="utf-8"))
        for prompt in data:
            cls.EXTRA_PROMPT[prompt["act"]] = prompt["prompt"]

    @classmethod
    async def load_conversation(
        cls, group_id: int, prompt_title: str
    ) -> list[dict[str, str]]:
        """加载上下文"""
        last_chat_log = await get_last_chat_log(group_id, prompt_title)
        return (
            ujson.loads(last_chat_log.conversation)
            if last_chat_log
            else cls.DEFOULT_CONVERSATION
        )

    @classmethod
    def token_str(cls, conversation: list[dict[str, str]]) -> str:
        return "\n".join([i["content"] for i in conversation])

    @classmethod
    def _get_token(cls, conversation: list[dict[str, str]]) -> int:
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens_per_message = 3
        tokens_per_name = 1
        num_tokens = 0
        for message in conversation:
            num_tokens += tokens_per_message
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":
                    num_tokens += tokens_per_name
        num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
        return num_tokens

    @classmethod
    async def get_token(cls, conversation: list[dict[str, str]]) -> int:
        return await asyncio.to_thread(cls._get_token, conversation)

    @classmethod
    async def check_token(
        cls, conversation: list[dict[str, str]], default_conversation_len: int = 1
    ):
        """保留一定的上下文，但不超过最大token数"""
        while await cls.get_token(conversation) > cls.MAX_TOKEN:
            if len(conversation) != default_conversation_len:
                conversation.pop(default_conversation_len)
            else:
                return

    @classmethod
    @aretry(times=3, exceptions=(APIError, ServerDisconnectedError, TimeoutError))
    async def _ask(cls, conversation: list[dict[str, str]]) -> _GptResponse:
        async with Session.proxy_session.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {cls.API_KEY}"},
            json={
                "model": "gpt-3.5-turbo",
                "messages": conversation,
                # kwargs
                "temperature": 0.7,
                "top_p": 1,
                "n": 1,
                "user": cls.ROLE,
            },
        ) as resp:
            if resp.status != 200:
                logger.error(await resp.text())
                raise APIError(f"respone {resp.status}")
            data = await resp.json()
        if "error" in data:
            raise APIError(data["error"]["message"])
        return _GptResponse(
            id=data["id"],
            object=data["object"],
            created=data["created"],
            role=data["choices"][0]["message"]["role"],
            text=data["choices"][0]["message"]["content"],
            token=data["usage"]["total_tokens"],
        )

    @classmethod
    async def ask(cls, group_id: int, user_id: int, prompt: str) -> str:
        config = await get_group_config(group_id)
        if not config:
            config = GroupConfig(
                group_id=group_id,
                role_id=0,
                prompt_title=cls.DEFOULT_PROMPT_TITLE,
                default_conversation=ujson.dumps(
                    cls.DEFOULT_CONVERSATION, ensure_ascii=False
                ),
            )
            await change_group_config(config)
        default_conversation_len = len(ujson.loads(config.default_conversation))
        sys_prompt_title = config.prompt_title if config else cls.DEFOULT_PROMPT_TITLE
        conversation = await cls.load_conversation(group_id, sys_prompt_title)
        conversation.append({"role": cls.ROLE, "content": prompt})
        await cls.check_token(conversation, default_conversation_len)
        try:
            response = await cls._ask(conversation)
        except ServerDisconnectedError:
            return "ChatGPT出错了: 服务器断开连接"
        except TimeoutError:
            return "ChatGPT出错了: 请求超时"
        except Exception as e:
            logger.exception(e)
            return f"ChatGPT出错了: {e}"
        conversation.append({"role": response.role, "content": response.text})
        await insert_chat_log(
            ChatLog(
                id=response.id,
                object=response.object,
                conversation=ujson.dumps(conversation, ensure_ascii=False),
                created=response.created,
                token=response.token,
                group_id=group_id,
                user_id=user_id,
                system_prompt_title=sys_prompt_title,
            )
        )
        return response.text

    @classmethod
    def role_to_conversation(cls, role: CustomRole) -> list[dict[str, str]]:
        """将role转化为对话记录"""
        conversation = cls.ROLE_TEMPLATE.copy()
        conversation.extend(
            [
                {"role": "user", "content": text.strip()}
                for text in role.role_prompt.split(cls.WRAP_LABEL)
            ]
        )
        conversation.append(cls.ENTERING_ROLE_PLAYING_MODE)
        conversation.append({"role": "assistant", "content": role.default_reply})
        return conversation

    @classmethod
    async def add_custom_role(cls, role: CustomRole):
        role = await add_custom_role(role)
        conversation = ujson.dumps(cls.role_to_conversation(role), ensure_ascii=False)
        config = GroupConfig(
            group_id=role.group_id,
            role_id=role.id,  # type: ignore
            prompt_title=role.role_name,
            default_conversation=conversation,
        )
        await change_group_config(config)
        await insert_chat_log(
            ChatLog(
                id=f"set-role-{datetime.now()}",
                object="set-role",
                created=int(datetime.timestamp(datetime.now())),
                conversation=conversation,
                token=0,
                group_id=role.group_id,
                user_id=role.member_id,
                system_prompt_title=role.role_name,
            )
        )
        return role

    @classmethod
    async def get_custom_role(cls, group: int) -> list[CustomRole]:
        return await get_custom_role_by_group(group)

    @classmethod
    async def remove_custom_role(cls, group: int, id: int):
        role = await get_custom_role_by_group(group, id)
        if not role:
            return None
        config = await get_group_config(group)
        if config.prompt_title == role[0].role_name:
            await cls.set_role(group, 0)
        await remove_custom_role_by_id(id)
        return role[0]

    @classmethod
    async def reset_chat(cls, group_id: int, user_id: int) -> None:
        """清除上下文"""
        # NOTE - 只要有消息记录，config绝对存在
        config = await get_group_config(group_id)

        log = ChatLog(
            id=f"reset-{datetime.now()}",
            object="reset",
            created=int(datetime.timestamp(datetime.now())),
            conversation=ujson.dumps(config.default_conversation, ensure_ascii=False),
            token=0,
            group_id=group_id,
            user_id=user_id,
            system_prompt_title=config.prompt_title,
        )
        await insert_chat_log(log)

    @classmethod
    async def reset_all_chat(cls):
        """清除所有上下文"""
        for group in await get_chatted_group_ids():
            await cls.reset_chat(group, 0)


chat = _Chatbot

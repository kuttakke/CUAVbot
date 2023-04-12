import asyncio
from asyncio.exceptions import TimeoutError
from dataclasses import dataclass
from datetime import datetime

import tiktoken
import ujson
from aiohttp.client_exceptions import ServerDisconnectedError
from loguru import logger

from utils.session import Session

from .service import (
    ChatLog,
    GroupConfig,
    change_group_config,
    count_chat_token,
    count_total_chat_token,
    get_chatted_group_ids,
    get_group_config,
    get_last_chat_log,
    insert_chat_log,
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
    API_KEY = ""
    ROLE = "user"
    DEFOULT_PROMPT = (
        "You are ChatGPT, a large language model trained by OpenAI."
        "Respond conversationally"
    )
    # 扮演群友
    # CHAT_PROMPT = (
    #     "Here is a chat log on the QQ platform"
    #     "(the speaker's name is before the colon and the message is after it"
    #     '; your message should start with "Me:"):'
    #     "\n\n{log}\n\n"
    #     "As a quirky, emotionally expressive, free-thinking member "
    #     "who likes to use emojis, you are tasked with driving the conversation forward."
    #     "Your replies should be in Chinese and no more than 25 characters. "
    #     "If the conversation becomes overly negative or serious, "
    #     "you may break this limit and express positive or optimistic sentiments. "
    #     "If the meaning of the conversation is unclear, "
    #     "you may simply express approval or disapproval, "
    #     'such as "Impressive 👍" starting with "Me:".'
    # )
    DEFOULT_PROMPT_TITLE = "ChatGPT"
    MAX_TOKEN = 3500
    PROMPT_URL = (
        "https://raw.githubusercontent.com/PlexPt/"
        "awesome-chatgpt-prompts-zh/main/prompts-zh.json"
    )
    EXTRA_PROMPT: dict[str, str] = {}
    is_sleep = False

    @classmethod
    def title_to_prompt(cls, title: str) -> str:
        if title == cls.DEFOULT_PROMPT_TITLE or title not in cls.EXTRA_PROMPT:
            return cls.DEFOULT_PROMPT
        sys_prompt = cls.EXTRA_PROMPT[title]
        if "填写你的称呼" in sys_prompt:
            return sys_prompt.replace("填写你的称呼", "哥哥")
        return sys_prompt

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
        config = GroupConfig(
            group_id=group_id,
            system_prompt=cls.DEFOULT_PROMPT_TITLE
            if role_id == 0
            else list(cls.EXTRA_PROMPT.keys())[role_id - 1],
        )
        await change_group_config(config)
        return config.system_prompt

    @classmethod
    async def load_prompt(cls) -> None:
        """加载额外提示"""
        async with Session.session.get(cls.PROMPT_URL) as resp:
            data = ujson.loads(await resp.text(encoding="utf-8"))
        for prompt in data:
            cls.EXTRA_PROMPT[prompt["act"]] = prompt["prompt"]

    @classmethod
    async def load_conversation(
        cls, group_id: int, user_id: int, prompt_title: str
    ) -> list[dict[str, str]]:
        """加载上下文"""
        last_chat_log = await get_last_chat_log(group_id, user_id, prompt_title)
        return (
            ujson.loads(last_chat_log.conversation)
            if last_chat_log
            else [{"role": "system", "content": cls.title_to_prompt(prompt_title)}]
        )

    @classmethod
    def token_str(cls, conversation: list[dict[str, str]]) -> str:
        return "\n".join([i["content"] for i in conversation])

    @classmethod
    def _get_token(cls, conversation: list[dict[str, str]]) -> int:
        return len(tiktoken.get_encoding("gpt2").encode(cls.token_str(conversation)))

    @classmethod
    async def get_token(cls, conversation: list[dict[str, str]]) -> int:
        return await asyncio.to_thread(cls._get_token, conversation)

    @classmethod
    async def check_token(cls, conversation: list[dict[str, str]]):
        """保留一定的上下文，但不超过最大token数"""
        while await cls.get_token(conversation) > cls.MAX_TOKEN:
            conversation.pop(1)

    @classmethod
    async def _ask(cls, conversation: list[dict[str, str]]) -> _GptResponse:
        # TODO 优化错误重试
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
        sys_prompt_title = config.system_prompt if config else cls.DEFOULT_PROMPT_TITLE
        conversation = await cls.load_conversation(group_id, user_id, sys_prompt_title)
        conversation.append({"role": cls.ROLE, "content": prompt})
        await cls.check_token(conversation)
        try:
            response = await cls._ask(conversation)
        except ServerDisconnectedError as e:
            logger.exception(e)
            return "ChatGPT出错了: 服务器断开连接"
        except TimeoutError as e:
            logger.exception(e)
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
    async def reset_chat(cls, group_id: int, user_id: int) -> None:
        """清除上下文"""
        config = await get_group_config(group_id)
        sys_prompt_title = config.system_prompt if config else cls.DEFOULT_PROMPT_TITLE
        conversation = [
            {"role": "system", "content": cls.title_to_prompt(sys_prompt_title)}
        ]
        log = ChatLog(
            id=f"reset-{datetime.now()}",
            object="reset",
            created=int(datetime.timestamp(datetime.now())),
            conversation=ujson.dumps(conversation, ensure_ascii=False),
            token=0,
            group_id=group_id,
            user_id=user_id,
            system_prompt_title=sys_prompt_title,
        )
        await insert_chat_log(log)

    @classmethod
    async def reset_all_chat(cls):
        """清除所有上下文"""
        for group in await get_chatted_group_ids():
            await cls.reset_chat(group, 0)


chat = _Chatbot

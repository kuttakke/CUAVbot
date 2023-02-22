import asyncio
from io import BytesIO
from pathlib import Path

import jieba.analyse
import pandas as pd
import wordcloud

from core.control import Controller
from core.entity import ChatGroupLog
from utils.msgtool import send_group


class WordCloudMaker:
    __wait_list = []
    __wait_list_lock = asyncio.Lock()
    __font_path = "./resources/fonts/OPPOSans-B.ttf"
    __stop_words_path = Path(__file__).parent / "stopwords.txt"
    __stop_words = set()
    __cache_save_path = Path(__file__).parent / "cache"

    @classmethod
    def __load_stop_words(cls):
        if not cls.__stop_words:
            cls.__stop_words.update(
                [
                    line.strip()
                    for line in cls.__stop_words_path.read_text(
                        encoding="utf-8"
                    ).splitlines()
                ]
            )

    @classmethod
    async def __get_member_log(
        cls, group_id, member_id, datetime
    ) -> list[ChatGroupLog]:
        return await Controller.get_chat_group_log(group_id, member_id, datetime)

    @classmethod
    def __from_log_to_df(cls, logs: list[ChatGroupLog]) -> pd.DataFrame:
        return pd.DataFrame([log.dict() for log in logs])

    @classmethod
    def __get_all_keywords(cls, df: pd.DataFrame) -> list[str]:
        words = []
        for msg in df["as_persistent_string"]:
            keywords = jieba.analyse.extract_tags(
                msg, topK=10, withWeight=False, allowPOS=("n",)
            )
            keywords = [word for word in keywords if word not in cls.__stop_words]
            words.extend(keywords)
        return words

    @classmethod
    def __word_to_series(cls, words: list[str]) -> pd.Series:
        s = pd.Series(words)
        s[s.str.len() > 1]
        return s.value_counts()

    @classmethod
    def __make_word_cloud(cls, logs: list[ChatGroupLog], time) -> bytes:
        df = cls.__from_log_to_df(logs)
        words = cls.__get_all_keywords(df)
        wc = wordcloud.WordCloud(
            font_path=cls.__font_path.__str__(),
            width=800,
            height=1200,
            background_color="black",
        )
        wc.generate_from_frequencies(cls.__word_to_series(words))
        wc.to_file(
            cls.__cache_save_path
            / f"{logs[0].group_id}-{logs[0].member_id}-{time.strftime('%Y%m%d')}.png"
        )
        img = BytesIO()
        wc.to_image().save(img, format="png")
        return img.getvalue()

    @classmethod
    async def make(cls, group_id, member_id, source, time):
        if not cls.__stop_words:
            cls.__load_stop_words()
        if (
            cache := (
                Path(__file__).parent
                / "cache"
                / f"{group_id}-{member_id}-{time.strftime('%Y%m%d')}.png"
            )
        ).exists():
            await send_group(group_id, cache.read_bytes(), quote=source)
        logs = await cls.__get_member_log(group_id, member_id, time)
        if logs.__len__() < 50:
            await send_group(group_id, "聊天记录不足50条，无法生成词云", quote=source)
            return
        await send_group(
            group_id,
            await asyncio.to_thread(cls.__make_word_cloud, logs, time),
            quote=source,
        )

    @classmethod
    async def loop_make(cls, group_id, member_id, source, datetime):
        async with cls.__wait_list_lock:
            if cls.__wait_list:
                cls.__wait_list.append((group_id, member_id, source, datetime))
                await send_group(
                    group_id,
                    f"有{cls.__wait_list.__len__() - 1}人正在生成词云，排队中",
                    quote=source,
                )
                return
        await send_group(group_id, "正在生成词云")
        await cls.make(group_id, member_id, source, datetime)
        while True:
            async with cls.__wait_list_lock:
                if not cls.__wait_list:
                    return
                group_id, member_id, source, datetime = cls.__wait_list.pop(0)
            await cls.make(group_id, member_id, source, datetime)

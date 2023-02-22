import asyncio
import json
import random
import time
import warnings
from asyncio import Lock
from datetime import datetime
from pathlib import Path

import jionlp as jio
from graia.ariadne import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Plain
from loguru import logger

__all__ = ("ClockController",)
__message__ = [
    "到点啦到点啦🥳",
    "z？是时候干点什么了😤",
    "有没有可能，现在该要干点什么了😕",
    "嗨老伙计！你是否快遗忘了某个重要的事情🤓",
    "本Bot似乎感受到了你现在需要干点什么🤔",
]

__lock__ = Lock()


class ClockTask:
    __slots__ = [
        "group",
        "member",
        "source",
        "delay",
        "origin_message",
        "_task",
        "create_date",
    ]

    def __init__(
        self,
        group: int,
        member: int,
        source: int,
        create_date: float,
        delay: float,
        origin_message: str,
    ):
        self.member = member
        self.create_date = create_date
        self.origin_message = origin_message
        self.delay = delay
        self.source = source
        self.group = group

        self._task: asyncio.Task | None = None

    async def _send(self):
        """发送闹钟内容"""
        app = Ariadne.current()
        is_quote = True
        msg = MessageChain([At(self.member), Plain(random.choice(__message__))])
        if not await self._is_source_exists():
            msg = msg.append(Plain(f"\n小本子上似乎写着：\n{self.origin_message}"))
            is_quote = False
        await app.send_group_message(
            self.group, msg, quote=(self.source if is_quote else None)
        )
        if await self._is_friend():
            group = await app.get_group(self.group)
            await app.send_friend_message(
                self.member,
                MessageChain(
                    f"一个闹钟在[{group.name if group else self.group}]触发了🥰:"
                    f"\n{self.origin_message}"
                ),
            )

    async def _send_fail(self):
        """发送闹钟失效信息"""
        app = Ariadne.current()
        if await self._is_friend():
            group = await app.get_group(self.group)
            await app.send_friend_message(
                self.member,
                MessageChain(
                    f"一个闹钟在[{group.name if group else self.group}]失效了😥:"
                    f"\n{self.origin_message}\n"
                    f"可能由于bot重启时间间隔过长"
                ),
            )
            return
        await app.send_group_message(
            self.group,
            MessageChain(
                [
                    At(self.member),
                    Plain(f"一个闹钟失效了😥:\n{self.origin_message}\n可能由于bot重启时间间隔过长"),
                ]
            ),
        )

    async def _is_source_exists(self) -> bool:
        try:
            await Ariadne.current().get_message_from_id(self.source)
        except BaseException as e:
            logger.error(e)
            return False
        return True

    async def _is_friend(self) -> bool:
        return bool(await Ariadne.current().get_friend(self.member))

    async def _wait_and_send(self):
        """闹钟的具体行为"""
        if (delay := (self.delay - (time.time() - self.create_date))) < 0:
            delay = 1
        await asyncio.sleep(delay)
        await self._send()
        await ClockController.cancel_task(self)

    @property
    def info(self):
        return self.origin_message

    async def run(self):
        """运行该闹钟"""
        if time.time() >= (self.create_date + self.delay):
            await self._send_fail()
            await ClockController.cancel_task(self)
            return
        self._task = asyncio.get_running_loop().create_task(self._wait_and_send())

    def cancel(self) -> "ClockTask":
        """将task取消"""
        if self._task and not self._task.done():
            self._task.cancel()
        return self

    @property
    def json(self) -> dict:
        return {
            "group": self.group,
            "member": self.member,
            "delay": self.delay,
            "create_date": self.create_date,
            "origin_message": self.origin_message,
            "source": self.source,
        }

    def __eq__(self, other) -> bool:
        return isinstance("ClockTask", other) and all(
            [
                self.create_date == other.create_date,
                self.member == other.member,
                self.group == other.group,
            ]
        )


class ClockController:
    """闹钟控制类"""

    _tasks: dict[str, list[ClockTask]] = {}
    _path = Path(__file__).parent / "info.json"

    @classmethod
    async def init(cls):
        """初始化"""
        if cls._path.exists():
            async with __lock__:
                info = json.loads(cls._path.read_text(encoding="utf-8")).items()
            for k, v in info:
                cls._tasks[k] = [ClockTask(**i) for i in v]
                for t in cls._tasks[k]:
                    await t.run()

    @classmethod
    async def _save(cls):
        """保存"""
        info = json.dumps({k: [t.json for t in v] for k, v in cls._tasks.items()})
        async with __lock__:
            cls._path.write_text(info, encoding="utf-8")
        # logger.debug("[AlarmClock] info file save ")

    @classmethod
    def _parse(cls, msg: str, create_date: float) -> float:
        """使用jionlp解析时间点字符串"""
        res = jio.parse_time(msg, time_base=time.time())
        if (
            ts := time.mktime(time.strptime(res["time"][0], "%Y-%m-%d %H:%M:%S"))
        ) < time.time():
            raise ValueError("该时间点已经随风而去了")
        return ts - create_date

    @classmethod
    def _parse_message(cls, msg: str, create_date: float) -> float:  # 😥我为什么要写这个
        """
        将 X小时|X分钟|X秒后、 今天|明天|后天 + x点x分x秒 的时间格式转换为具体delay
        :param msg: 包含一个时间节点的字符串
        :param create_date: 该任务创建日期 float
        :return: delay: int 应该进行的sleep秒数
        """
        warnings.warn("使用jionlp去解析中文时间字符串", DeprecationWarning)
        date_head = {"今天": 0, "明天": 86400, "后天": 172800}
        if msg[:2] in date_head:
            time_list = (
                msg[2:].replace("点", " ").replace("分", " ").replace("秒", " ").split()
            )
            args = {
                ["hour", "minute", "second"][i]: int(time_list[i])
                for i in range(len(time_list))
            }
            delay = (
                datetime.fromtimestamp(create_date + date_head[msg[:2]])
                .replace(**args)
                .timestamp()
                - create_date
            )
        else:
            date_head = {"时": 3600, "钟": 60, "秒": 1}  # 小时后、分钟后、秒后 所以是[-2]
            delay = (
                int(msg[:-1].replace("小时", "").replace("分钟", "").replace("秒", ""))
                * date_head[msg[-2]]
            )
        if not delay:
            raise ValueError("delay为0")
        return delay

    @classmethod
    async def _send_msg(
        cls, msg: str, group: int, member: int, source: int | None = None
    ):
        """发送消息"""
        app = Ariadne.current()
        await app.send_group_message(
            group, MessageChain([At(member), Plain(msg)]), quote=source
        )

    @classmethod
    async def add_task(
        cls,
        group: int,
        member: int,
        source: int,
        create_date: float,
        origin_message: str,
    ):
        """添加闹钟task"""
        try:
            delay = cls._parse(origin_message.split()[0], create_date)
        except BaseException as e:
            logger.error(e)
            await cls._send_msg(f"闹钟设置遇到了错误：\n{e}\n您是否在输入一些奇怪的东西🤔", group, member)
        else:
            if not cls._tasks.get(key := f"{group}{member}", None):
                cls._tasks[key] = []
            cls._tasks[key].append(
                task := ClockTask(
                    group, member, source, create_date, delay, origin_message
                )
            )
            await task.run()
            await cls._send_msg("该闹钟设置成功", group, member, source)
            await cls._save()

    @classmethod
    async def cancel_task(cls, task: ClockTask):
        """取消该task"""
        cls._tasks[(key := f"{task.group}{task.member}")].remove(task.cancel())
        if not cls._tasks[key]:
            cls._tasks.pop(key)
        await cls._save()

    @classmethod
    def tasks_info(cls, group: int, member: int) -> str | None:
        """获取该member设置了的闹钟"""
        if ts := cls._tasks.get(f"{group}{member}", None):
            return f"共设置了{len(ts)}个闹钟:\n" + "\n".join(
                f"闹钟{i + 1}: {ts[i].info}" for i in range(len(ts))
            )

    @classmethod
    def get_task(cls, group: int, member: int, index: int = 0) -> ClockTask | None:
        """以下标方式获取该member的task实例"""
        if ts := cls._tasks.get(f"{group}{member}", None):
            if index <= len(ts):
                return ts[index]

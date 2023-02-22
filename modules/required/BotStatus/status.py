import asyncio
import os
import platform
import time
from importlib.metadata import version
from pathlib import Path

import pkg_resources
import psutil
from aiohttp import ClientTimeout
from graia.ariadne import Ariadne
from loguru import logger
from psutil import Process

from utils.session import Session
from utils.t2i import template2img
from utils.tool import random_banner


class StatusInfo:
    package_list = [i.key for i in pkg_resources.working_set if i.key.startswith("graia")]  # type: ignore
    package_list.extend(["launart", "statv"])
    package_info: str
    system_name: str  # 系统名
    system_version: int  # type: ignore # 系统版本
    cpu_platform: str  # CPU架构平台
    cpu_logicl_count: int  # CPU逻辑核心
    cpu_physics_count: int  # CPU物理核心
    cpu_brand: str  # CPU品牌信息
    cpu_freq: int  # CPU频率 单位GHz
    cpu_percent: float  # CPU所有逻辑核心占用情况
    memory_total: int  # 总虚拟内存
    memory_used: int  # 已使用虚拟内存
    memory_left_percent: float  # 剩余内存占比
    pid: Process  # 本程序pid
    pid_memory: int  # 本程序使用内存
    pid_create_time: int  # 创建时间
    mirai_htto_api: str  # Mirai-http-api版本
    python_version: str  # python版本
    init_status: bool = False

    @classmethod
    def _init_pid(cls):
        cls.pid = psutil.Process(os.getpid())
        cls.pid_create_time = cls.pid.create_time()

    @classmethod
    def _package_versions(cls):
        out = "".join(f"\n{i}: {version(i)}" for i in cls.package_list)
        cls.package_info = out

    @classmethod
    def _package_versions_list(cls):
        return [f"{i}: {version(i)}" for i in cls.package_list]

    @classmethod
    async def google_ping(cls, proxy: bool = False):
        try:
            if proxy:
                async with Session.proxy_session.get(
                    "https://www.google.com", timeout=ClientTimeout(total=5)
                ) as resp:
                    return resp.status == 200
            async with Session.session.get(
                "https://www.google.com", timeout=ClientTimeout(total=5)
            ) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(e)
            return False

    @classmethod
    def _flash(cls):
        if not cls.init_status:
            cls.system_name: str = platform.system()  # 系统名
            cls.system_version: str = platform.version()  # 系统版本
            cls.cpu_platform: str = platform.machine()  # CPU架构平台
            cls.cpu_logicl_count: int = psutil.cpu_count()  # type: ignore # CPU逻辑核心
            cls.cpu_physics_count: int = psutil.cpu_count(logical=False)  # type: ignore  # CPU物理核心
            cls.cpu_brand: str = platform.processor()  # CPU品牌信息
            cls.cpu_freq: int = psutil.cpu_freq().current  # type: ignore  # CPU频率 单位GHz
            cls.memory_total: int = psutil.virtual_memory().total  # 总虚拟内存
            cls._init_pid()
            cls._package_versions()
            cls.python_version = platform.python_version()
            cls.init_status = True
        cls.memory_used: int = psutil.virtual_memory().used  # 已使用虚拟内存
        cls.memory_left_percent: float = psutil.virtual_memory().percent  # 剩余内存占比
        cls.pid_memory = cls.pid.memory_info().rss
        cls.cpu_percent = psutil.cpu_percent(interval=0.1)  # type: ignore # 堵塞io

    @classmethod
    @property
    def info_str(cls):  # sourcery skip: inline-immediately-returned-variable
        cls._flash()
        info = (
            "## 系统详情："
            f"\n{cls.system_name} {cls.system_version} - {cls.cpu_platform}"
            f"\nCPU: {cls.cpu_brand}"
            f"\nCPU逻辑/物理核心：{cls.cpu_logicl_count}/{cls.cpu_physics_count} - {'%.2f' % (cls.cpu_freq / 1024)}Ghz"
            f"\nCPU占用：{'%.2f' % cls.cpu_percent}%\n"
            "## 内存："
            f"<总:{'%.2f' % (cls.memory_total / 1073741824)}GB> "
            f"<已用:{'%.2f' % (cls.memory_used / 1073741824)}GB> "
            f"<剩余：{cls.memory_left_percent}%>\n"
            f"## Bot信息："
            f"\npython版本:{cls.python_version}"
            f"{cls.package_info}"
            f"\nMirai-http-api:{cls.mirai_htto_api}"
            f"\nBot占用内存： {'%.2f' % (cls.pid_memory / 1048576)}MB"
            f"\n启动于: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(cls.pid_create_time))}"
        )
        return info

    @classmethod
    async def info_img_bytes(cls) -> bytes:
        cls._flash()
        app = Ariadne.current()
        running_time = time.time() - cls.pid_create_time
        day = int(running_time / 86400)
        hour = int(running_time % 86400 / 3600)
        minute = int(running_time % 86400 % 3600 / 60)
        second = int(running_time % 86400 % 3600 % 60)
        running_time = f'{f"{day}d " if day else ""}{f"{hour}h " if hour else ""}{f"{minute}m " if minute else ""}{second}s'
        (
            cls.mirai_htto_api,
            google_ping,
            google_ping_proxy,
            banner,
        ) = await asyncio.gather(
            app.get_version(),
            cls.google_ping(),
            cls.google_ping(proxy=True),
            random_banner(),
        )
        info_list = cls._package_versions_list()
        info_list.append(f"Mirai-http-api:{cls.mirai_htto_api}")
        info_list.append(f"Bot占用内存： {'%.2f' % (cls.pid_memory / 1048576)}MB")
        info_list.append(
            f"启动于: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(cls.pid_create_time))}"
        )
        info_list.append(f"运行时间: {running_time}")
        if len(info_list) % 3:
            info_list.extend([None for _ in range(3 - len(info_list) % 3)])  # type: ignore
        return await template2img(
            Path(__file__).parent / "status.html",
            {
                "title": "CUAV-Bot状态",
                "banner": banner,
                "subtitle": "created by CUAV-BOT",
                "system_info": f"{cls.system_name} {cls.system_version} - {cls.cpu_platform}",
                "cpu_info": f"{cls.cpu_brand} <br>&emsp; {cls.cpu_logicl_count}/{cls.cpu_physics_count} - {'%.2f' % (cls.cpu_freq / 1024)}Ghz - {'%.2f' % cls.cpu_percent}%",
                "memory_info": f"<总:{'%.2f' % (cls.memory_total / 1073741824)}GB> <已用:{'%.2f' % (cls.memory_used / 1073741824)}GB> <剩余：{cls.memory_left_percent}%>",
                "is_local_pass": google_ping,
                "is_proxy_pass": google_ping_proxy,
                "info_list": info_list,
            },
        )


if __name__ == "__main__":
    print(StatusInfo.info_str)
    print(
        "当前进程的VMS内存使用：%.4f MB"
        % (psutil.Process(os.getpid()).memory_info().vms / 1024 / 1024)
    )
    print(
        "当前进程的RSS内存使用：%.4f MB"
        % (psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024)
    )

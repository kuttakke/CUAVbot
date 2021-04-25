from graia.saya import Saya
import os
from typing import List, Optional
import json
from pathlib import Path
from graia.application.logger import AbstractLogger
import loguru
import sys

master_id: Optional[int] = None

_logger_save_path = "./log/bot{time}.log"


class ModuleLoader:
    @classmethod
    def load(cls, saya: Saya):
        modules = "modules.{}"
        with saya.module_context():
            for module_name in cls._get_module_str():
                saya.require(modules.format(module_name))

    @classmethod
    def _get_module_str(cls) -> List[str]:
        module_str_list = []
        file_list = os.listdir("./modules")
        for file in file_list:
            if not file.startswith("_"):
                module_str_list.append(file.split(".")[0])
        return module_str_list


class BotAttributes:
    def __init__(self, json_path: str):
        self.json_path = json_path
        self.host: Optional[str] = None
        self.authKey: Optional[str] = None
        self.account: Optional[str] = None
        self.master: Optional[str] = None
        self._initialization_attributes()

    def _initialization_attributes(self):
        path = Path(self.json_path)
        json_data = json.loads(path.read_text(encoding="utf-8"))
        self.host = json_data["host"]
        self.authKey = json_data["authKey"]
        self.account = json_data["account"]
        self.master = json_data["qq"]["master"]
        global master_id
        master_id = self.master


class MyLogger(AbstractLogger):
    def __init__(self) -> None:
        """
        自建logger
        """
        path = _logger_save_path
        format_str = "[{time:YYYY-MM-DD HH:mm:ss,SSS}][{level}]: {message}"
        self.logger = loguru.logger
        self.logger.remove(handler_id=None)
        self.logger.add(sys.stderr, format=format_str, level="INFO")
        self.logger.add(sink=path, rotation='00:00', retention='10 days', level="INFO", format=format_str)

    def info(self, msg):
        return self.logger.info(msg)

    def error(self, msg):
        return self.logger.error(msg)

    def debug(self, msg):
        return self.logger.debug(msg)

    def warn(self, msg):
        return self.logger.warning(msg)

    def exception(self, msg):
        return self.logger.exception(msg)


logger = MyLogger()

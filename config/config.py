import json


class Config:
    def __init__(self):
        self.__help_path = "./config/help"
        self.__config_path = "./config/config.json"
        self.__dnd_help_path = "./config/dnd"

    def set_config(self):
        with open(self.__config_path, "r", encoding="utf-8") as f:
            config = json.loads(f.read())
        return config

    def set_help(self):
        with open(self.__help_path, "r", encoding="utf-8") as f:
            help_ = f.read()
        return help_

    def set_dnd_help(self):
        with open(self.__dnd_help_path, "r", encoding="utf-8") as f:
            help_ = f.read()
        return help_
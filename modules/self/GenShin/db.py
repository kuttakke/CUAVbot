from datetime import datetime
from pathlib import Path

from PIL import ImageFont
from pydantic import BaseModel
from tinydb import TinyDB
from tinydb.queries import where

__all__ = ["GenShinUser", "GenShinSignLog", "GenShinDb", "DailyNoteInfo", "Settings"]


class GenShinUser(BaseModel):
    qq_id: int
    uid: int
    cookies: str
    sign_enable: bool = True
    resin_remind_enable: bool = True
    create_date: datetime
    next_remind_date: datetime | None = None

    class Config:
        json_encoders = {datetime: lambda x: x.strftime("%Y-%m-%d %H:%M:%S")}
        json_decoders = {datetime: lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S")}

    def dict(self):
        return {
            k: v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v
            for k, v in self.__dict__.items()
            if v is not None
        }


class GenShinSignLog(BaseModel):
    qq_id: int
    uid: int
    sign_date: datetime
    rewords: str
    count: int

    class Config:
        json_encoders = {datetime: lambda x: x.strftime("%Y-%m-%d %H:%M:%S")}
        json_decoders = {datetime: lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S")}

    def dict(self):
        return {
            k: v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v
            for k, v in self.__dict__.items()
            if v is not None
        }


class DailyNoteInfo(BaseModel):
    # 探索派遣
    current_expedition_num: int
    max_expedition_num: int
    expedition_remained_time: str

    # 洞天宝钱
    current_home_coin: int
    max_home_coin: int
    home_coin_recovery_time: str

    # 原粹树脂
    current_resin: int
    max_resin: int
    resin_recovery_time: str

    # 值得铭记的强敌/周本树脂减半次数
    remain_resin_discount_num: int
    resin_discount_num_limit: int
    resin_discount_msg: str

    # 每日委托任务
    finished_task_num: int
    total_task_num: int
    task_msg: str

    # 参量质变仪
    transformer: str
    transformer_recovery_time: str

    # 给loop.task设置的sleep time
    user_id: int
    sleep_time: int
    next_date: datetime

    class Config:
        json_encoders = {datetime: lambda x: x.strftime("%Y-%m-%d %H:%M:%S")}
        json_decoders = {datetime: lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S")}

    def dict(self):
        return {
            k: v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v
            for k, v in self.__dict__.items()
            if v is not None
        }


class GenShinDb:
    user_path = Path(__file__).parent / "genshin_user.json"
    sign_path = Path(__file__).parent / "genshin_sign_log.json"
    _db_user = TinyDB(user_path)
    db_user = _db_user.table("user")
    db_sign = TinyDB(sign_path)

    @classmethod
    def _search_user(cls, qq_id: int, uid: int | None = None) -> list[dict] | None:
        if uid:
            return (
                cls.db_user.search((where("uid") == uid) & (where("qq_id") == qq_id))  # type: ignore
                or None
            )

        return cls.db_user.search((where("qq_id") == qq_id))  # type: ignore

    @classmethod
    def get_user(cls, qq_id: int) -> list[GenShinUser]:
        return [
            GenShinUser.parse_obj(json_dict) for json_dict in cls._search_user(qq_id)  # type: ignore
        ]

    @classmethod
    def get_specific_user(cls, qq_id: int, uid: int) -> GenShinUser | None:
        if json_list := cls._search_user(qq_id, uid):
            return GenShinUser.parse_obj(json_list[0])

    @classmethod
    def get_all_user(cls) -> list[GenShinUser]:
        return [GenShinUser.parse_obj(json_dict) for json_dict in cls.db_user.all()]

    @classmethod
    def insert_user(cls, user: GenShinUser):
        cls.db_user.insert(user.dict())

    @classmethod
    def insert_sign_log(cls, sign_log: GenShinSignLog):
        cls.db_sign.table(f"{sign_log.qq_id}").insert(sign_log.dict())

    @classmethod
    def update_user(cls, user: GenShinUser):
        cls.db_user.upsert(
            user.dict(), (where("qq_id") == user.qq_id) & (where("uid") == user.uid)  # type: ignore
        )

    @classmethod
    def delete_user(cls, user: GenShinUser):
        cls.db_user.remove((where("qq_id") == user.qq_id) & (where("uid") == user.uid))  # type: ignore

    @classmethod
    def delete_user_by_qq_id(cls, qq_id: int):
        cls.db_user.remove((where("qq_id") == qq_id))  # type: ignore


class Settings:
    # Salt = "h8w582wxwgqvahcdkpvdhbh2w9casgfl"
    Salt = "9nQiU3AV0rJSIBWgdynfoGMGKaklfbM7"
    # NoteSalt = "dWCcD2FsOUXEstC5f9xubswZxEeoBOTc"
    NoteSalt = "xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs"
    # Version = "2.3.0"
    Version = "2.33.1"
    SignVersion = "2.34.1"
    ClientType = "5"
    SignClientType = "2"

    ActId = "e202009291139501"
    WebApi = "https://api-takumi.mihoyo.com"
    HostRecord = "https://api-takumi-record.mihoyo.com"
    AccountInfoUrl = f"{WebApi}/binding/api/getUserGameRolesByCookie?game_biz=hk4e_cn"
    SignRewordsUrl = f"{WebApi}/event/bbs_sign_reward/home?act_id={ActId}"
    SignCheckUrl = (
        f"{WebApi}/event/bbs_sign_reward/info?act_id={ActId}" + "&region={}&uid={}"
    )
    SignUrl = f"{WebApi}/event/bbs_sign_reward/sign"
    DailyNoteUrl = (
        f"{HostRecord}/game_record/app/genshin/api/dailyNote" + "?role_id={}&server={}"
    )
    file_path = Path(__file__).parent
    daily_info_keys = {
        0: {
            "name": "原粹树脂",
            "img": f"{file_path}/resource/树脂2.png",
            "bottom": "resin_recovery_time",
            "right": ["current_resin", "max_resin"],
        },
        1: {
            "name": "洞天宝钱",
            "img": f"{file_path}/resource/洞天宝钱2.png",
            "bottom": "home_coin_recovery_time",
            "right": ["current_home_coin", "max_home_coin"],
        },
        2: {
            "name": "每日委托任务",
            "img": f"{file_path}/resource/委托2.png",
            "bottom": "task_msg",
            "right": ["finished_task_num", "total_task_num"],
        },
        3: {
            "name": "探索派遣",
            "img": f"{file_path}/resource/派遣2.png",
            "bottom": "expedition_remained_time",
            "right": ["current_expedition_num", "max_expedition_num"],
        },
        4: {
            "name": "值得铭记的强敌",
            "img": f"{file_path}/resource/周本2.png",
            "bottom": "resin_discount_msg",
            "right": ["remain_resin_discount_num", "resin_discount_num_limit"],
        },
        5: {
            "name": "参量质变仪",
            "img": f"{file_path}/resource/参量质变仪2.png",
            "bottom": "transformer_recovery_time",
            "right": "transformer",
        },
    }

    # img

    font_italic_path = "./resources/fonts/OPPOSans-B.ttf"
    font_normal_path = "./resources/fonts/sarasa-mono-sc-semibold.ttf"
    font_italic = ImageFont.truetype(font_italic_path, 26)
    font_italic_sm = ImageFont.truetype(font_italic_path, 18)
    font_normal = ImageFont.truetype(font_normal_path, 24)

    back_color = (241, 234, 226)
    id_color = (209, 187, 140)
    text_color = (104, 96, 93)
    item_color = (245, 242, 235)
    line_color = (227, 218, 209)
    text_color2 = (32, 31, 26)
    text_color3 = (171, 168, 162)

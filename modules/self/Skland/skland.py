from dataclasses import dataclass
from typing import Any

import aiohttp

from .entity import AttendanceLog, User
from .service import add_attendance_log, add_user


@dataclass
class State:
    code: int
    info: str


@dataclass
class Player:
    uid: int
    name: str
    channel: str


class Skland:
    URL_ATTENDANCE = "https://zonai.skland.com/api/v1/game/attendance"
    URL_PLAYER_BINDING = "https://zonai.skland.com/api/v1/game/player/binding?"
    HEADERS = {
        "User-Agent": "Skland/1.0.1 (com.hypergryph.skland; build:100001014; Android 25; ) Okhttp/4.11.0",
    }
    temp_user_info: dict[int, list[Player]] = {}

    @classmethod
    async def _reward_handler(cls, user: User, rewards: list[dict[str, Any]]):
        info = "签到奖励：\n"
        for reward in rewards:
            await add_attendance_log(
                attendance_log=AttendanceLog(
                    qid=user.qid,
                    uid=user.uid,
                    count=reward["count"],
                    rid=reward["resource"]["id"],
                    rname=reward["resource"]["name"],
                    rtype=reward["resource"]["type"],
                )
            )
            info += f'{reward["count"]} * [{reward["resource"]["name"]} ({reward["resource"]["type"]})]\n'
        return info.strip()

    @classmethod
    def _player_info_handler(cls, qid: int, players: list[dict[str, Any]]) -> str:
        uids: list[Player] = []
        info = "角色信息：\n编号   UID      区服      名称\n"
        for index, player in enumerate(players):
            info += f"{index+1}  {player['uid']}  {player['channelName']}  {player['nickName']}"
            uids.append(
                Player(player["uid"], player["nickName"], player["channelName"])
            )
        cls.temp_user_info[qid] = uids
        return info

    @classmethod
    async def get_user_info(
        cls, session: aiohttp.ClientSession, cred_token: str, qid: int
    ) -> State:
        headers = cls.HEADERS.copy()
        headers["cred"] = cred_token
        print(headers)
        async with session.get(cls.URL_PLAYER_BINDING, headers=headers) as res:
            res_data = await res.json()

        if (code := res_data["code"]) != 0:
            return State(code, res_data["message"])
        info = cls._player_info_handler(qid, res_data["data"]["list"][0]["bindingList"])
        return State(0, info)

    @classmethod
    async def add_user(cls, cred_token: str, qid: int, index: int):
        info = cls.temp_user_info[qid][index - 1]
        await add_user(
            User(
                qid=qid,
                uid=info.uid,
                cred=cred_token,
                token=None,
                name=info.name,
                channel=info.channel,
            )
        )

    @classmethod
    async def attendance(cls, session: aiohttp.ClientSession, user: User) -> State:
        headers = cls.HEADERS.copy()
        headers["cred"] = user.cred

        async with session.post(
            cls.URL_ATTENDANCE,
            headers=headers,
            data={"uid": str(user.uid), "gameId": 1},
        ) as res:
            res_data = await res.json()
        code = res_data["code"]
        if code != 0:
            return State(code=code, info=res_data["message"])
        data = res_data["data"]

        info = await cls._reward_handler(user, data["awards"])
        return State(code=code, info=info)


skland = Skland

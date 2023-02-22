import asyncio
import hashlib
import random
import re
import string
import time
import uuid
from asyncio import Task, to_thread
from datetime import datetime, timedelta
from io import BytesIO

import aiohttp
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image as EImage
from graia.ariadne.message.element import Plain
from loguru import logger
from PIL import Image, ImageDraw

from utils.msgtool import send_debug, send_friend, send_group

from .db import DailyNoteInfo, GenShinDb, GenShinSignLog, GenShinUser, Settings


class GenShinError(Exception):
    pass


class Controller:
    _remind_task: Task | None = None
    _disable_sign: bool = False
    _signed_uids: set = set()
    _retry_uids: set = set()
    _alredy_remind_uids: set = set()  # 已经提醒过的uid，每24小时重置一次

    @classmethod
    def _ds(cls) -> str:
        i = str(int(time.time()))
        r = "".join(random.sample(string.ascii_lowercase + string.digits, 6))
        md5 = hashlib.md5()
        md5.update(f"salt={Settings.Salt}&t={i}&r={r}".encode())
        return f"{i},{r},{md5.hexdigest()}"

    @staticmethod
    def _note_ds(query: str = ""):
        i = str(int(time.time()))
        r = random.randint(100000, 900000)
        md5 = hashlib.md5()
        md5.update(f"salt={Settings.NoteSalt}&t={i}&r={r}&b=&q={query}".encode())
        return f"{i},{r},{md5.hexdigest()}"

    @classmethod
    def _device_id(cls, cookies: str) -> str:
        return str(uuid.uuid3(uuid.NAMESPACE_URL, cookies)).replace("-", "").upper()

    @classmethod
    def reset_signed_uids(cls):
        cls._signed_uids.clear()

    @classmethod
    def make_headers(cls, user: GenShinUser) -> dict:
        return {
            "Accept": "application/json, text/plain, */*",
            "DS": cls._ds(),
            "Origin": "https://webstatic.mihoyo.com",
            "x-rpc-app_version": Settings.SignVersion,
            "User-Agent": f" miHoYoBBS/{Settings.SignVersion}",
            "x-rpc-client_type": Settings.ClientType,
            "Referer": "https://webstatic.mihoyo.com/bbs/event/signin-ys/index.html?bbs_auth_required=true&act_id"
            f"={Settings.ActId}&utm_source=bbs&utm_medium=mys&utm_campaign=icon",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,en-US;q=0.8",
            "X-Requested-With": "com.mihoyo.hyperion",
            "Cookie": user.cookies,
            "x-rpc-device_id": cls._device_id(user.cookies),
        }

    @classmethod
    def make_note_headers(cls, user: GenShinUser, query: str) -> dict:
        return {
            "Accept": "application/json, text/plain, */*",
            "DS": cls._note_ds(query),
            "Origin": "https://webstatic.mihoyo.com",
            "x-rpc-app_version": Settings.Version,
            "User-Agent": f" miHoYoBBS/{Settings.Version}",
            "x-rpc-client_type": Settings.ClientType,
            "Referer": "https://webstatic.mihoyo.com/bbs/event/signin-ys/index.html?bbs_auth_required=true&act_id"
            f"={Settings.ActId}&utm_source=bbs&utm_medium=mys&utm_campaign=icon",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,en-US;q=0.8",
            "X-Requested-With": "com.mihoyo.hyperion",
            "Cookie": user.cookies,
            "x-rpc-device_id": cls._device_id(user.cookies),
        }

    @classmethod
    async def _fetch(
        cls,
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        headers: dict,
        json: dict | None = None,
        _is_retry: bool = False,
    ) -> dict:
        # logger.info(f"{method} {url}")
        # logger.info(f"{headers}")
        try:
            async with session.request(method, url, headers=headers, json=json) as resp:
                data = await resp.json()
                if data["retcode"] not in [0, -5003]:
                    raise GenShinError(f"[原神助手]请求{url}失败，返回{data}")
                return data
        except Exception as e:
            if _is_retry:
                raise e
            logger.error(f"[原神助手]请求{url}失败，重试")
            return await cls._fetch(session, method, url, headers, json, _is_retry=True)

    @classmethod
    def _get_uid_from_cookies(cls, cookies: str) -> int:
        return int(re.findall(r"account_id=\d+", cookies)[0].replace("account_id=", ""))

    @classmethod
    async def _get_account_list(
        cls, session: aiohttp.ClientSession, user: GenShinUser
    ) -> list:
        data = await cls._fetch(
            session,
            "GET",
            Settings.AccountInfoUrl,
            cls.make_headers(user)
            # headers,
        )
        return [
            (i["nickname"], i["game_uid"], i["region"], i["level"])
            for i in data["data"]["list"]
        ]

    @classmethod
    async def get_info(cls, user: GenShinUser) -> str:
        async with aiohttp.ClientSession() as session:
            return "".join(
                f"昵称：{name} 等级: {level} 地区:{region}\n"
                for name, _, region, level in await cls._get_account_list(session, user)
            ).strip()

    @classmethod
    async def get_sign_rewords(
        cls, session: aiohttp.ClientSession, user: GenShinUser
    ) -> list[dict]:
        data = await cls._fetch(
            session,
            "GET",
            Settings.SignRewordsUrl,
            cls.make_headers(user),
        )
        return data["data"]["awards"]

    @classmethod
    async def _fetch_daily_note(
        cls,
        session: aiohttp.ClientSession,
        user: GenShinUser,
        region: str,
        game_id: int,
    ) -> dict:
        url = Settings.DailyNoteUrl.format(game_id, region)
        data = await cls._fetch(
            session,
            "GET",
            url,
            cls.make_note_headers(user, url.split("?")[1]),
        )
        return data["data"]

    @classmethod
    def _get_recover_time(cls, data: dict) -> tuple[str, int, datetime]:
        if data["current_resin"] == data["max_resin"]:
            resin_recovery_time = "树脂已完全恢复"
            sleep_time = 0
        else:
            sleep_time = int(data["resin_recovery_time"])
            rrd = datetime.fromtimestamp(time.time() + sleep_time)
            day = "今天" if rrd.day - datetime.now().day == 0 else "明天"
            resin_recovery_time = f"将于{day} {rrd.hour}:{rrd.minute} 全部恢复"

        return (
            resin_recovery_time,
            sleep_time,
            datetime.now() + timedelta(seconds=sleep_time),
        )

    @classmethod
    def _get_home_coin_recovery_time(cls, data: dict) -> str:
        if data["current_home_coin"] == data["max_home_coin"]:
            return "存储已满"
        coin_recovery_time = int(data["home_coin_recovery_time"])
        day = coin_recovery_time // 86400
        hour = coin_recovery_time % 86400 // 3600
        minute = coin_recovery_time % 86400 % 3600 // 60
        time_str = (
            f"{f'{str(day)}天' if day else ''}{f'{str(hour)}小时' if hour else ''}"
            f"{f'{str(minute)}分钟' if minute else ''} "
        )

        return f"预计{time_str or '一分钟'}后达到上限"

    @classmethod
    def _get_expedition_remained_time(cls, data: dict) -> str:
        now = datetime.now()
        if data["current_expedition_num"] == 0:
            expedition_remained_time = "未开始派遣"
        else:
            remained_time = 0
            for expedition in data["expeditions"]:
                if int(expedition["remained_time"]) > remained_time:
                    remained_time = int(expedition["remained_time"])
            if remained_time:
                ert = datetime.fromtimestamp(time.time() + remained_time)
                day = "今天" if ert.day - now.day == 0 else "明天"
                expedition_remained_time = f"将于{day} {ert.hour}:{ert.minute} 完成"
            else:
                expedition_remained_time = "派遣已完成"
        return expedition_remained_time

    @classmethod
    def _get_transformer(cls, data: dict) -> tuple[str, str]:
        trt = data["transformer"]
        transformer_status = "冷却中"
        if not trt["obtained"]:
            transformer_recovery_time = "尚未获得"
            transformer_status = "未获得"
        else:
            time_dict = trt["recovery_time"]
            time_str_t = (
                f"{str(time_dict['Day']) + '天' if time_dict['Day'] else ''}"
                f"{str(time_dict['Hour']) + '小时' if time_dict['Hour'] else ''}"
                f"{str(time_dict['Minute']) + '分钟' if time_dict['Minute'] else ''}"
            )
            if time_str_t or time_dict["Second"]:
                transformer_recovery_time = f"预计{time_str_t or '一分钟'}后准备完成"
            else:
                transformer_status = "可使用"
                transformer_recovery_time = "已准备完成"
        return transformer_status, transformer_recovery_time

    @classmethod
    def _make_daily_note_info(cls, data: dict, uid: int) -> DailyNoteInfo:
        resin_recovery_time, sleep_time, next_date = cls._get_recover_time(data)
        data.pop("resin_recovery_time")
        home_coin_recovery_time = cls._get_home_coin_recovery_time(data)
        task_msg = f"今日委托奖励{'已' if data['finished_task_num'] == data['total_task_num'] else '未'}领取"
        data.pop("home_coin_recovery_time")
        expedition_remained_time = cls._get_expedition_remained_time(data)
        resin_discount_msg = (
            "周本树脂减半次数已用" if data["remain_resin_discount_num"] != 0 else "周本已完成"
        )
        transformer_status, transformer_recovery_time = cls._get_transformer(data)
        data.pop("transformer")
        return DailyNoteInfo(
            **data,
            expedition_remained_time=expedition_remained_time,
            home_coin_recovery_time=home_coin_recovery_time,
            resin_recovery_time=resin_recovery_time,
            resin_discount_msg=resin_discount_msg,
            task_msg=task_msg,
            transformer=transformer_status,
            transformer_recovery_time=transformer_recovery_time,
            user_id=uid,
            sleep_time=sleep_time,
            next_date=next_date,
        )

    @classmethod
    async def get_daily_note_info(cls, user: GenShinUser) -> list[DailyNoteInfo]:
        info_list = []
        async with aiohttp.ClientSession() as session:
            accounts = await cls._get_account_list(session, user)
            for _, uid, region, _ in accounts:
                data = await cls._fetch_daily_note(session, user, region, uid)
                info_list.append(cls._make_daily_note_info(data, uid))
        return info_list

    @classmethod
    async def sign_info(
        cls, session: aiohttp.ClientSession, user: GenShinUser, region: str, uid: int
    ) -> dict:
        data = await cls._fetch(
            session,
            "GET",
            Settings.SignCheckUrl.format(region, uid),
            cls.make_headers(user),
        )
        return data["data"]

    @classmethod
    async def _send_bound_error(cls, user: GenShinUser, error: Exception) -> None:
        logger.error(f"[原神助手]@{user.qq_id}绑定失败，{error}")
        logger.exception(error)
        await send_friend(user.qq_id, "获取账号信息失败，请检查cookies或联系管理员")
        await send_debug(f"[原神助手]@{user.qq_id}绑定失败，{error}")

    @classmethod
    async def _send_bound_success(cls, user: GenShinUser, info: str) -> None:
        logger.info(f"[原神助手]@{user.qq_id}绑定成功，{info}")
        await send_friend(user.qq_id, f"绑定成功，{info}")
        await send_debug(f"[原神助手]@{user.qq_id}绑定成功，{info}")
        await send_friend(user.qq_id, "[原神助手]默认开启每日自动签到和树脂提醒，更多指令请使用[.用法 原神助手]获取")

    @classmethod
    async def _send_not_specified_error(cls, qq: int) -> None:
        await send_friend(qq, "您绑定了多个账号，请使用-u来指定uid，更多命令请使用[.用法 原神助手]获取")

    @classmethod
    async def _send_not_bound_error(cls, qq: int) -> None:
        await send_friend(qq, "您还没有绑定账号，更多命令请使用[.用法 原神助手]获取")

    @classmethod
    async def _send_uid_not_found_error(cls, qq: int) -> None:
        await send_friend(qq, "您指定的uid不存在，请检查uid是否正确")

    @classmethod
    async def _send_meaningless_error(cls, qq: int) -> None:
        await send_friend(qq, "指令重复，属性并未改变")

    @classmethod
    async def _send_sign_error(cls, qq: int, error: Exception) -> None:
        await send_friend(qq, f"[原神助手]签到失败，请检查cookies或联系管理员， 返回值：{error}")
        await send_debug(f"[原神助手]@{qq}签到失败，{error}")
        logger.error(f"[原神助手]@{qq}签到失败，{error}")

    @classmethod
    async def _send_cookies_change_error(cls, qq: int, error: Exception) -> None:
        await send_friend(qq, f"[原神助手]cookies改变失败，请检查cookies或联系管理员， 返回值：{error}")
        await send_debug(f"[原神助手]@{qq}cookies改变失败，{error}")
        logger.error(f"[原神助手]@{qq}cookies改变失败，{error}")

    @classmethod
    async def _send_remind_error(cls, error: Exception) -> None:
        await send_debug(f"[原神助手]树脂提醒失败，task将在下次重置时启动{error}")
        logger.exception(error)

    @classmethod
    async def create_user(cls, qq_id: int, cookies: str) -> GenShinUser | None:
        if GenShinDb.get_specific_user(
            qq_id, uid := cls._get_uid_from_cookies(cookies)
        ):
            await send_friend(qq_id, "该账号已经绑定过了o(╥﹏╥)o")
            return
        user = GenShinUser(
            qq_id=qq_id,
            uid=uid,
            cookies=cookies,
            create_date=datetime.now(),
        )
        # logger.info(f"{'==='*10}新建用户\n{user}")
        try:
            info = await cls.get_info(user)
            # logger.info(f"{'==='*10}获取用户信息\n{info}")
        except Exception as e:
            await cls._send_bound_error(user, e)
        else:
            await cls._send_bound_success(user, info)
            GenShinDb.insert_user(user)
            return user

    @classmethod
    async def _locate_user(
        cls, qq_id: int, uid: int | None = None
    ) -> GenShinUser | None:
        if not uid:
            users = GenShinDb.get_user(qq_id)
            if len(users) >= 2:
                await cls._send_not_specified_error(qq_id)
                return
            if not users:
                await cls._send_not_bound_error(qq_id)
                return
            user = users[0]
        else:
            user = GenShinDb.get_specific_user(qq_id, uid)
            if not user:
                await cls._send_uid_not_found_error(qq_id)
                return
        return user

    @classmethod
    async def disable_auto_sign(cls, qq_id: int, uid: int | None = None) -> None:
        if not (user := await cls._locate_user(qq_id, uid)):
            return
        if not user.sign_enable:
            await cls._send_meaningless_error(qq_id)
            return
        user.sign_enable = False
        GenShinDb.update_user(user)
        await send_friend(qq_id, f"[原神助手]已关闭uid:{user.uid}的自动签到")

    @classmethod
    async def enable_auto_sign(cls, qq_id: int, uid: int | None = None) -> None:
        if not (user := await cls._locate_user(qq_id, uid)):
            return
        if user.sign_enable:
            await cls._send_meaningless_error(qq_id)
            return
        user.sign_enable = True
        GenShinDb.update_user(user)
        await send_friend(qq_id, f"[原神助手]已开启uid:{user.uid}的自动签到")

    @classmethod
    async def disable_resin_remind(cls, qq_id: int, uid: int | None = None) -> None:
        if not (user := await cls._locate_user(qq_id, uid)):
            return
        if not user.resin_remind_enable:
            await cls._send_meaningless_error(qq_id)
            return
        user.resin_remind_enable = False
        GenShinDb.update_user(user)
        await send_friend(qq_id, f"[原神助手]已关闭uid:{user.uid}的树脂提醒")

    @classmethod
    async def enable_resin_remind(cls, qq_id: int, uid: int | None = None) -> None:
        if not (user := await cls._locate_user(qq_id, uid)):
            return
        if user.resin_remind_enable:
            await cls._send_meaningless_error(qq_id)
            return
        user.resin_remind_enable = True
        GenShinDb.update_user(user)
        await send_friend(qq_id, f"[原神助手]已开启uid:{user.uid}的树脂提醒")

    # 关闭全局签到
    @classmethod
    def disable_global_sign(cls) -> None:
        cls._disable_sign = True

    # 开启全局签到
    @classmethod
    def enable_global_sign(cls) -> None:
        cls._disable_sign = False

    @classmethod
    async def update_cookies(
        cls, qq_id: int, cookies: str, uid: int | None = None
    ) -> None:
        if not (user := await cls._locate_user(qq_id, uid)):
            return
        user.cookies = cookies
        try:
            info = await cls.get_info(user)
        except Exception as e:
            await cls._send_cookies_change_error(user.qq_id, e)
        else:
            await send_friend(qq_id, f"[原神助手]已更新uid:{user.uid}的cookies\n{info}")
            GenShinDb.update_user(user)

    @classmethod
    async def remove_user(cls, qq_id: int, uid: int | None = None) -> None:
        if not (user := await cls._locate_user(qq_id, uid)):
            return
        GenShinDb.delete_user(user)
        await send_friend(qq_id, f"[原神助手]已删除uid:{user.uid}的绑定")

    @classmethod
    async def remove_user_by_admin(cls, qq_id: int) -> None:
        GenShinDb.delete_user_by_qq_id(qq_id)
        await send_debug(f"[原神助手]已删除qq:{qq_id}的绑定")

    @classmethod
    async def sign_single(cls, user: GenShinUser) -> None:
        async with aiohttp.ClientSession() as session:
            accounts = await cls._get_account_list(session, user)
            if not accounts:
                await send_friend(user.qq_id, f"[原神助手]签到失败，旅行者{user.uid}似乎没有绑定原神")
                return
            for nick_name, game_uid, region, _ in accounts:
                data = await cls.sign_info(session, user, region, game_uid)
                if data["first_bind"]:
                    await send_friend(
                        user.qq_id, f"原神签到失败，旅行者{nick_name}似乎是首次绑定原神，请先手动签到一次哦~✨"
                    )
                    continue
                if data["is_sign"]:
                    logger.info(f"旅行者{nick_name}今日已签到")
                    await send_friend(user.qq_id, f"[原神助手]旅行者{nick_name}今日已签到")
                    cls._signed_uids.add(user.uid)
                    continue
                sign_result = await cls._fetch(
                    session,
                    "POST",
                    Settings.SignUrl,
                    cls.make_headers(user),
                    {"act_id": Settings.ActId, "region": region, "uid": game_uid},
                )
                rewords_total = await cls.get_sign_rewords(session, user)
                sign_days = data["total_sign_day"]
                rewords_name = rewords_total[sign_days]["name"]
                rewords_count = int(rewords_total[sign_days]["cnt"])
                match sign_result["retcode"]:
                    case 0:
                        if sign_result["data"]["success"] != 0:
                            await send_friend(
                                user.qq_id, f"[原神助手]签到失败，旅行者{nick_name}触发了验证码，无法自动签到"
                            ) if user.uid not in cls._retry_uids else None  # 如果是重试的，则不再发送提醒
                            raise GenShinError("CAPTCHA triggered")
                        await send_friend(
                            user.qq_id,
                            f"[原神助手]签到成功，旅行者{nick_name}已签到{sign_days}天，漏签{data['sign_cnt_missed']}天\n"
                            f"获得 {rewords_name}x{rewords_count}",
                        )
                        GenShinDb.insert_sign_log(
                            GenShinSignLog(
                                qq_id=user.qq_id,
                                uid=user.uid,
                                sign_date=datetime.now(),
                                rewords=rewords_name,
                                count=rewords_count,
                            )
                        )
                        cls._signed_uids.add(user.uid)
                    case -5003:
                        logger.info(f"[原神助手]旅行者{nick_name}今日已签到")

    @classmethod
    async def sign(cls):
        if cls._disable_sign:
            return
        all_user = GenShinDb.get_all_user()
        for user in all_user:
            if user.sign_enable and user.uid not in cls._signed_uids:
                try:
                    await cls.sign_single(user)
                except Exception as e:
                    logger.error(e)
                    cls._retry_uids.add(user.uid)
                await asyncio.sleep(1)
        await cls.retry_sign(list(filter(lambda x: x.uid in cls._retry_uids, all_user)))

    @classmethod
    async def retry_sign(cls, users: list[GenShinUser], _times: int = 0) -> None:
        if not users:
            return
        _times += 1
        if _times == 4:
            cls._retry_uids.clear()
            return
        for user in users:
            try:
                await cls.sign_single(user)
            except Exception as e:
                logger.error(e)
                cls._retry_uids.add(user.uid)
                if _times == 3:
                    await send_friend(user.qq_id, "[原神助手]三次签到重试全部失败")
            else:
                cls._retry_uids.remove(user.uid)
            await asyncio.sleep(5)
        await cls.retry_sign(
            list(filter(lambda x: x in cls._retry_uids, users)), _times
        )

    @classmethod
    def _make_daily_note_img(cls, info: DailyNoteInfo) -> bytes:
        image = Image.new("RGB", (600, 584), Settings.back_color)  # type: ignore
        draw = ImageDraw.Draw(image)
        img_id = Image.new("RGB", (7, 40), Settings.id_color)  # type: ignore
        image.paste(img_id, (20, 8))

        content_img = Image.new("RGB", (530, 80), Settings.line_color)  # type: ignore
        item_img = Image.new("RGB", (530 - 170, 76), Settings.item_color)  # type: ignore
        bk_img2 = Image.open(f"{Settings.file_path}/resource/bg2.png").resize((160, 80))

        draw.text(
            (30, 16),
            f"ID: {info.user_id}",
            font=Settings.font_italic,
            fill=Settings.text_color,
        )

        # 月-日 时：分 星期*
        now = datetime.now()
        weekday_info = {0: "一", 1: "二", 2: "三", 3: "四", 4: "五", 5: "六", 6: "天"}
        date_str = f"{now.month}-{now.day} {now.hour}:{now.minute} 星期{weekday_info[now.weekday()]}"
        date_str_size = Settings.font_italic.getsize(date_str)
        draw.text(
            (584 - 20 - date_str_size[0], 16),
            date_str,
            font=Settings.font_italic,
            fill=Settings.text_color,
        )

        for i in range(6):
            now_y = 56 + ((80 + 8) * i)
            image.paste(content_img, (20, now_y))
            image.paste(item_img, (20 + 2, now_y + 2))
            k = Settings.daily_info_keys[i]
            img_resin2 = Image.open(k["img"])
            image.paste(img_resin2, (20 + 20, now_y + 20), img_resin2)
            r = Settings.daily_info_keys[i]["right"]
            if isinstance(Settings.daily_info_keys[i]["right"], list):
                right_msg = (
                    f"{info.__getattribute__(r[0])}/{info.__getattribute__(r[1])}"
                )
            else:
                right_msg = info.__getattribute__(r)
            right_msg_size = Settings.font_italic.getsize(right_msg)
            draw.text(
                (
                    380 + 85 - (right_msg_size[0] // 2),
                    now_y + 40 - (right_msg_size[1] // 2),
                ),
                right_msg,
                font=Settings.font_italic,
                fill=Settings.text_color,
            )
            draw.text(
                (80 + 10, now_y + 10),
                k["name"],
                font=Settings.font_normal,
                fill=Settings.text_color2,
            )
            image.paste(bk_img2, (20, now_y), bk_img2)
            draw.text(
                (80 + 10, now_y + 45),
                info.__getattribute__(k["bottom"]),
                font=Settings.font_italic_sm,
                fill=Settings.text_color3,
            )
        imageio = BytesIO()
        image.save(
            imageio,
            format="JPEG",
            quality=90,
            subsampling=2,
            qtables="web_high",
        )
        return imageio.getvalue()

    @classmethod
    async def _get_sleep_time(cls, user: GenShinUser) -> float:
        next_date = min(
            await cls.get_daily_note_info(user), key=lambda note: note.next_date
        ).next_date
        user.next_remind_date = next_date
        GenShinDb.update_user(user)
        return (next_date - datetime.now()).total_seconds()

    @classmethod
    async def _get_curren_remind(
        cls, is_init: bool = False
    ) -> tuple[GenShinUser, float] | None:
        users = [
            user
            for user in GenShinDb.get_all_user()
            if user.resin_remind_enable and user.uid not in cls._alredy_remind_uids
        ]
        sleep_time_list = [
            (user.next_remind_date - datetime.now()).total_seconds()
            if user.next_remind_date and is_init
            else await cls._get_sleep_time(user)
            for user in users
        ]
        return (
            min(tuple(zip(users, sleep_time_list)), key=lambda x: x[1])
            if users
            else None
        )

    @classmethod
    def is_task_running(cls) -> bool:
        return (
            not (cls._remind_task.done())
            if isinstance(cls._remind_task, Task)
            else False
        )

    @classmethod
    async def _task_runner(
        cls,
        user: GenShinUser | None = None,
        sleep_time: float | None = None,
        _is_retry: bool = False,
    ) -> None:
        if not sleep_time:
            # 12小时
            sleep_time = 43200
        if not _is_retry:
            await asyncio.sleep(sleep_time)
        if user:
            try:
                info = await cls.get_daily_note_info(user)
                for note in info:
                    if note.current_resin != note.max_resin:
                        continue
                    img_bytes = await to_thread(cls._make_daily_note_img, note)
                    msg = MessageChain(
                        [Plain("[原神助手]树脂已满哦~"), EImage(data_bytes=img_bytes)]
                    )
                    await send_friend(user.qq_id, msg)
            except Exception as e:
                if _is_retry:
                    await cls._send_remind_error(e)
                    raise e
                else:
                    await cls._task_runner(user, sleep_time, True)

            cls._alredy_remind_uids.add(user.uid)
        await cls.resin_reminder()

    @classmethod
    async def reset_reminder(cls):
        cls._alredy_remind_uids.clear()
        if not cls.is_task_running() and cls.enable_resin_remind:
            await cls.resin_reminder()

    @classmethod
    async def resin_reminder(cls, is_init: bool = False) -> None:
        curren_remind = await cls._get_curren_remind(is_init)
        if curren_remind:
            user, sleep_time = curren_remind
            function = cls._task_runner(user, sleep_time)
        else:
            function = cls._task_runner()
        loop = asyncio.get_running_loop()
        cls._remind_task = loop.create_task(function)
        logger.info("[原神助手] reminder task started")

    @classmethod
    async def get_resin(cls, qq: int, uid: int | None = None):
        if user := await cls._locate_user(qq, uid):
            bytes_list = [
                await to_thread(cls._make_daily_note_img, info)
                for info in await cls.get_daily_note_info(user)
            ]
            for bytes_ in bytes_list:
                await send_friend(qq, bytes_)

    @classmethod
    async def get_resin_by_group(cls, group: int, qq: int, uid: int | None = None):
        if user := await cls._locate_user(qq, uid):
            bytes_list = [
                await to_thread(cls._make_daily_note_img, info)
                for info in await cls.get_daily_note_info(user)
            ]
            for bytes_ in bytes_list:
                await send_group(group, bytes_)

    @classmethod
    async def manual_sign(cls, qq: int, uid: int | None = None):
        if user := await cls._locate_user(qq, uid):
            await cls.sign_single(user)

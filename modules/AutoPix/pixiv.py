from pixivpy_async import AppPixivAPI as Api
from typing import Tuple, List, Union, Optional
from graia.application.entry import (
    Plain, Image
)
from io import BytesIO
import copy
import aiohttp
from aiohttp_proxy import ProxyType, ProxyConnector
import aiofile
import json
import os
from loguru import logger


class Pixiv:
    def __init__(self,
                 account: int,
                 a_token: str,
                 r_token: str,
                 recent_update: list,
                 save_path: str,
                 logger_,
                 proxy: Optional[str]):
        """
        Pixiv对象，储存个人账号信息进行更新、下载（不支持gif），支持代理(SOCKS5)，支持自定义logger
        :param account: qq账号id
        :param a_token: Pixiv账号access_token
        :param r_token: Pixiv账号refresh_token
        :param recent_update: 最近更新列表
        :param save_path: 图片存储路径
        :param logger_: 日志对象
        :param proxy: 代理链接
        """
        if proxy:
            self.api = Api(proxy=proxy)
        else:
            self.api = Api()
        self.skip_page = "ugoira"
        # self.save_path = "./function/pixiv_img"
        self.save_path = save_path
        self.account = account
        self.a_token = a_token
        self.r_token = r_token
        self.recent_update = recent_update
        self.proxy = proxy
        self.login_command()
        self.logger = logger_

    def login_command(self):
        """
        使用内置的token设置登录pix
        :return:
        """
        self.api.set_auth(self.a_token, self.r_token)

    async def refresh_token(self):
        """
        依据内置的refresh_token进行token刷新，同时进行token登录设置
        :return:
        """
        a, r = await Pix.reset_token(self.account, self.r_token)
        self.a_token = a
        self.r_token = r
        self.logger.info("{}的重置Token：'access_token - {}' 'refresh_token - {}'".format(str(self.account), a, r))
        self.login_command()
        self.logger.info("{}的Token 写入文件成功".format(str(self.account)))

    async def _get_new_follow_art(self, retry: bool = False):
        """
        获取关注列表的新图，列表结果已进行比对筛选去除已更新
        :param retry: 当token失效自动刷新登录，无需手动设置
        :return: 图片列表[[pid,page]...]
        """
        try:
            self.logger.info("向api请求中")
            json_all = await self.api.illust_follow()
        except BaseException as e:
            self.logger.error(e)
        else:
            if "error" in json_all and retry is False:
                self.logger.info("{}的Token失效".format(str(self.account)))
                await self.refresh_token()
                return await self._get_new_follow_art(retry=True)
            self.logger.info("Token有效，获得数据中")
            real_pid_list = []
            json_res = json_all["illusts"]
            last_save_pid_list = self.recent_update
            art_list = []
            nums = 0
            for img in json_res:
                pid = str(img['id'])
                if img['type'] == self.skip_page or pid in last_save_pid_list:
                    pass
                else:
                    meta_single_page = img['meta_single_page']
                    meta_pages = img['meta_pages']
                    if meta_single_page:
                        art_list.append([pid, meta_single_page['original_image_url']])
                    elif meta_pages:
                        pages = []
                        for page in meta_pages:
                            pages.append(page['image_urls']["original"])
                        art_list.append([pid, pages])
                    nums += 1
                real_pid_list.append(pid)
                if nums >= 20:
                    break
            self.logger.info("json数据获取结束")
            return art_list, real_pid_list

    @classmethod
    def _resolve_art_list(cls, art_list: list):
        """
        根据结果对url列表进行分离整合
        :param art_list: Pix_url_list
        :return: pid列表, 单个pid包含图片数列表， 纯url列表
        """
        pid_list = []
        pages_count_list = []
        url_list = []
        for art in art_list:
            pid_list.append(art[0])
            pages_info = art[1]
            if isinstance(pages_info, str):
                pages_info = [pages_info]
            pages_count_list.append(len(pages_info))
            url_list.extend(pages_info)

        return pid_list, pages_count_list, url_list

    async def _url_to_path(self, urls: List[str]) -> \
            Tuple[List[str], List[List[Union[int, str]]], List[List[Union[int, BytesIO]]]]:
        """
        根据url列表，转化为储存路径列表，并对url进行反向代理链接替换
        :param urls: url_list
        :return: paths: Tuple[List[str],
                url_list: List[List[Union[int, str]]], downloaded_img: List[List[Optional[int, BytesIO]]]]
        """
        if isinstance(urls, str):
            urls = [urls]
        paths = []
        num_to_urls = list(zip([i for i in range(len(urls))], urls))
        downloaded_img = []
        url_list = []
        for url in num_to_urls:
            path = os.path.join(self.save_path, url[1].split("/")[-1])
            if os.path.exists(path):
                async with aiofile.async_open(path, "rb") as f:
                    downloaded_img.append([url[0], BytesIO(await f.read())])
            else:
                url_list.append([url[0], url[1].replace("i.pximg.net", "i.pixiv.cat")])
                # url_list.append([url[0], url[1]])
                paths.append(path)
        return paths, url_list, downloaded_img

    @classmethod
    async def _downloader(cls, download_url: List[List[Union[int, str]]], logger, proxy: Optional[str] = None) \
            -> List[List[Union[int, BytesIO]]]:
        """
        下载所有图片链接， 返回二进制数据列表
        :param download_url: url_list
        :return: bytes_data_list
        """
        down = []
        index_date = [i[0] for i in download_url]
        n = 0
        if proxy:
            proxy_info_list = proxy.split(":")
            port = int(proxy_info_list[-1])
            ip = proxy_info_list[1].split("/")[-1]
            # hander = {
            #     "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4471.0 Safari/537.36 Edg/91.0.864.1",
            #     "Referer": "https://www.pixiv.net/"
            # }
            connector = ProxyConnector(proxy_type=ProxyType.SOCKS5, host=ip, port=port)
            async with aiohttp.ClientSession(connector=connector) as session:
                for url in download_url:
                    logger.info(f"请求url：{url}")
                    img = await cls._aiohttp_down(session, url)
                    down.append([index_date[n], img])
                    n += 1
        else:
            async with aiohttp.ClientSession() as session:
                for url in download_url:
                    img = await cls._aiohttp_down(session, url)
                    down.append([index_date[n], img])
                    n += 1
        return down

    @classmethod
    async def _aiohttp_down(cls, session: aiohttp.ClientSession, url: list[Union[int, str]], re: int = 0):
        async with session.get(url[1]) as response:
            if response.status == 200:
                img = BytesIO(await response.read())
                return img
            else:
                if re > 3:
                    raise ConnectionError
                else:
                    return await cls._aiohttp_down(session, url, re + 1)

    @classmethod
    def _zip_img(cls, downloaded: List[List[Union[int, BytesIO]]], now_download: List[List[Union[int, BytesIO]]]) -> \
            List[BytesIO]:
        """
        合并
        :param downloaded:
        :param now_download:
        :return:
        """
        size_img = len(downloaded) + len(now_download)
        res_list = [BytesIO()] * size_img
        for i in downloaded:
            res_list[i[0]] = i[1]
        for i in now_download:
            res_list[i[0]] = i[1]
        return res_list

    async def _save_from_downloader(self, pages_path: list, img_bytes: List[List[Union[int, BytesIO]]]):
        """
        下载至对应路径
        :param pages_path: list
        :param img_bytes: List[BytesIO]
        :return:
        """
        img_len = len(pages_path)
        for i in range(img_len):
            async with aiofile.async_open(pages_path[i], "wb") as f:
                await f.write(img_bytes[i][1].getvalue())
        self.logger.info("{}张图片保存成功".format(str(img_len)))

    def _creat_msg_chain(self, pid_list: List[str], pages_num: List[int], img_bytes: List[BytesIO]):
        """
        进行消息链构造
        :param pid_list: List[str]
        :param pages_num: List[int]
        :param img_bytes: List[BytesIO]
        :return: List[List[MessageChain], ...]
        """
        page_count = 0
        msg_img_limit = 2
        limit_count = 0
        out_msg_list = [[Plain("又到了涩图时间！此次共有{}张图!".format(str(len(img_bytes))))]]
        for i in range(len(pid_list)):
            out_msg = []
            for n in range(pages_num[i]):
                out_msg.append(Image.fromUnsafeBytes(img_bytes[page_count].getvalue()))
                page_count += 1
                limit_count += 1
                if limit_count >= msg_img_limit:
                    limit_count = 0
                    out_msg_list.extend([out_msg])
                    out_msg = []
            if out_msg:
                out_msg_list.extend([out_msg])
                limit_count = 0
        self.logger.info("消息链构建成功")
        return out_msg_list

    async def _change_recent_save(self, pid: list):
        """
        保存更新作品pid
        :param pid: list
        :return:
        """
        await Pix.change_recent_save(self.account, pid)
        self.logger.info("{}的最近更新已正常写入".format(str(self.account)))

    async def run(self):
        """
        pix更新
        :return: List[List[MessageChain], ...]
        """
        self.logger.info("即将获取更新列表")
        res, last_pid_list = await self._get_new_follow_art()
        if not res:
            self.logger.info("操作完成，无作品更新")
            pass
        else:
            self.logger.info("json分离结束")
            pid_list, pages_num, url_list = self._resolve_art_list(res)
            self.logger.info("进行链接代理转化")
            pages_path, new_urls, downloaded_bt_list = await self._url_to_path(url_list)
            self.logger.info("进行下载")
            img_bytes = await self._downloader(new_urls, self.logger, self.proxy)
            self.logger.info("下载完成,进行打包")
            fin_img_list = self._zip_img(downloaded_bt_list, img_bytes)
            self.logger.info("打包完成，保存至本地文件")
            await self._save_from_downloader(pages_path, img_bytes)
            self.logger.info("保存完毕，开始构建消息链")
            out_msg_list = self._creat_msg_chain(pid_list, pages_num, fin_img_list)
            await self._change_recent_save(last_pid_list)
            self.recent_update = last_pid_list
            return out_msg_list


class Pix:
    _path: Optional[str] = None
    _img_save_path: Optional[str] = None
    _proxy: Optional[str] = None
    _logger = None

    def __init__(self, account_path: str, img_save_path: str, logger_=None, proxy: Optional[str] = None):
        """
        Pix对象，实例化时，读取json数据生成Pixiv对象列表，支持功能开关, 支持多人
        :param account_path: json数据保存路劲
        :param img_save_path: 图片存储路径
        :param logger_: 日志对象
        :param proxy: 代理
        """
        self.auto = True
        self._path = account_path
        self._img_save_path = img_save_path
        if logger_:
            self.logger = logger_
        else:
            self.logger = logger
        self._change_global_obj(account_path, img_save_path, self.logger, proxy)
        self.proxy = proxy
        self.pix_obj_list = self._initialize_pix_object()

    @classmethod
    def _change_global_obj(cls, account_path, img_save_path, logger_, proxy):
        cls._path = account_path
        cls._img_save_path = img_save_path
        cls._logger = logger_
        cls._proxy = proxy

    @classmethod
    async def read_pix_json_async(cls) -> dict:
        async with aiofile.async_open(cls._path, "r") as f:
            pix_account = json.loads(await f.read())
        return pix_account["pixiv_account"]

    @classmethod
    def read_pix_json(cls) -> dict:
        """
        读取json数据
        :return:
        """
        with open(cls._path, "r", encoding="utf-8") as f:
            pix_account = json.loads(f.read())
        return pix_account

    def get_account_list(self):
        return [i[0] for i in self.pix_obj_list]

    def set_auto_update(self, com: str):
        code_ = com.split()[-1]
        if code_ == "0":
            self.auto = False
            return [Plain("自动更新已关闭")]
        elif code_ == "1":
            self.auto = True
            return [Plain("自动更新已开启")]

    @classmethod
    async def change_json(cls, data: dict) -> None:
        """
        修改json数据
        :param data: dict
        :return: None
        """
        async with aiofile.async_open(cls._path, "w") as f:
            await f.write(json.dumps(data, indent=4, ensure_ascii=True))

    def _initialize_pix_object(self) -> List[List[Union[int, Pixiv]]]:
        """
        构造Pixiv对象列表
        :return: [[id,PixivObjet], ...]
        """
        pix_account = self.read_pix_json()["pixiv_account"]
        pix_obj_list = []
        for pix in pix_account:
            account = pix["account"]
            token = pix["token"]
            recent_update = pix["recent_update"]
            pix_obj_list.append([account, Pixiv(
                account, token[0], token[1], recent_update, self._img_save_path, self.logger, self.proxy
            )])
        self.logger.info("Pix初始化成功")
        return pix_obj_list

    @classmethod
    async def reset_token(cls, account: int, r_token: str) -> Tuple[str, str]:
        a, r = await cls.refresh(r_token)
        n = 0
        pix_account = await cls.read_pix_json_async()
        new_ = copy.deepcopy(pix_account)
        for pix in pix_account:
            if pix["account"] == account:
                new_[n]["token"] = [a, r]
                break
            else:
                n += 1
        data = {"pixiv_account": new_}
        await cls.change_json(data)
        return a, r

    @classmethod
    async def refresh(cls, refresh_token):
        """
        token刷新请求
        :param refresh_token:
        :return: (access_token, refresh_token)
        """
        url = "https://oauth.secure.pixiv.net/auth/token"
        data = {
            "client_id": "MOBrBDS8blbauoSck0ZfDbtuzpyT",
            "client_secret": "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj",
            "grant_type": "refresh_token",
            "include_policy": "true",
            "refresh_token": refresh_token,
        }
        headers = {"User-Agent": "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)"}
        if cls._proxy:
            proxy_info_list = cls._proxy.split(":")
            port = int(proxy_info_list[-1])
            ip = proxy_info_list[1].split("/")[-1]
            connector = ProxyConnector(proxy_type=ProxyType.SOCKS5, host=ip, port=port)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(url=url, data=data, headers=headers) as response:
                    res = await response.json()
        else:
            async with aiohttp.ClientSession() as session:
                async with session.post(url=url, data=data, headers=headers) as response:
                    res = await response.json()
        try:
            access_token = res["access_token"]
            refresh_token = res["refresh_token"]
        except BaseException as error:
            cls._logger.error(f"error:\n{error}")
            cls._logger.info(f"返回消息\n{res}")
        else:
            return access_token, refresh_token

    @classmethod
    async def change_recent_save(cls, account: int, pid: list) -> None:
        """
        修改最近更新图片
        :param account: qqid
        :param pid: 更新列表
        :return: None
        """
        pix_account = await cls.read_pix_json_async()
        new_ = copy.deepcopy(pix_account)
        n = 0
        for pix in pix_account:
            if pix["account"] == account:
                new_[n]["recent_update"] = pid
                break
            else:
                n += 1
        data = {"pixiv_account": new_}
        await cls.change_json(data)

    async def run(self, fri_account: int):
        self.logger.info("即将遍历obj列表")
        for obj in self.pix_obj_list:
            if obj[0] == fri_account:
                self.logger.info("找到obj，即将.run()运行")
                return await obj[1].run()
        return [Plain("没有找到您的pixiv账号信息")]

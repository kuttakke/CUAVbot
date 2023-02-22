import base64
import random
import time
from pathlib import Path

from loguru import logger

from utils.session import Session


def remove_duplicates_from_obj(obj_list: list, need_rd_list: list, obj_target: str):
    out_list = need_rd_list.copy()
    for i in obj_list:
        if i.__getattribute__(obj_target) in need_rd_list:
            out_list.remove(i.__getattribute__(obj_target))
    return out_list


# 时间戳转换为距离现在的时间段字符串
def timestamp_to_period_str(timestamp: int | float) -> str:
    """
    时间戳转换为距离现在的时间段字符串
    Example: "1天前" 、 "1小时前"

    Args:
        timestamp (int): _description_

    Returns:
        str: _description_
    """
    now = time.time()
    suffix = "前" if timestamp < now else "后"
    if (timestamp := now - timestamp if timestamp < now else timestamp - now) < 60:
        return "刚刚"
    elif timestamp < 3600:
        return f"{int(timestamp / 60)}分钟{suffix}"
    elif timestamp < 86400:
        return f"{int(timestamp / 3600)}小时{suffix}"
    elif timestamp < 604800:
        return f"{int(timestamp / 86400)}天{suffix}"
    elif timestamp < 2592000:
        return f"{int(timestamp / 604800)}周{suffix}"
    elif timestamp < 31536000:
        return f"{int(timestamp / 2592000)}月{suffix}"
    else:
        return f"{int(timestamp / 31536000)}年{suffix}"


def to_module_file_name(path: Path) -> str:
    """
    将文件路径转换为模块名

    Args:
        path (Path): 模块主文件的路径

    Returns:
        str: 模块名
    """
    return path.parent.stem if path.stem == "__init__" else path.stem


BANNER_PATH = Path("./resources/banner")


async def random_pc_pic() -> str:
    async with Session.session.get("https://api.maho.cc/random-img/pc.php") as response:
        response.raise_for_status()
        data = await response.read()
        if not (file := BANNER_PATH / response.url.path.split("/")[-1]).exists():
            file.write_bytes(data)  # NOTE - 存起来避免api失效
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"


async def random_banner() -> str:
    try:
        return await random_pc_pic()
    except Exception as e:
        logger.exception(e)
        path_list = list(BANNER_PATH.iterdir())
        path = random.sample(path_list, 1)[0]
        return f"data:image/png;base64,{base64.b64encode(path.read_bytes()).decode()}"


if __name__ == "__main__":
    print(timestamp_to_period_str(1659906053))

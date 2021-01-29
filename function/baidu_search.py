from urllib.parse import quote

def u_can_baidu(word:str):
    url = "https://www.baidu.com/s?ie=UTF-8&wd={}"
    key = quote(word.replace(".baidu", "").replace("。baidu", "").strip())
    return url.format(key)



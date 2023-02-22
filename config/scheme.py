from dataclasses import dataclass


@dataclass
class Mirai:
    """Mirai http api 配置"""

    host: str
    key: str
    account: int
    master: int
    debug_group: int
    admins: list[int]
    modules_base_path: str
    core_modules_path: str
    self_modules_path: str
    bot_name: str
    master_name: str
    debug_module: list[str]


@dataclass
class Proxy:
    """代理配置"""

    host: str
    port: int
    type: str


@dataclass
class Saucenao:
    api_key: str


@dataclass
class Pix:
    save_path: str


@dataclass
class TencentCloud:
    secret_id: str
    secret_key: str


@dataclass
class BotConf:
    """主配置文件"""

    mirai: Mirai
    proxy: Proxy
    saucenao: Saucenao
    pix: Pix
    tencent_cloud: TencentCloud

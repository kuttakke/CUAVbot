from typing import Optional

from dynaconf import Dynaconf, base

settings: Optional[base.LazySettings] = None

settings_file = "./config/settings.toml"


def config_init():
    global settings
    settings = Dynaconf(
        envvar_prefix="DYNACONF",
        settings_files=[settings_file],
    )


config_init()


# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.

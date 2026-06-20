from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="all-in-one",
    description="",
    usage="",
    config=Config,
)

from nonebot import require

require("nonebot_plugin_alconna")

from . import handle

__all__ = ["handle"]

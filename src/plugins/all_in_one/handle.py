from datetime import datetime, timedelta, timezone

from arclet.alconna import Alconna, Args, StrMulti, Subcommand
from nonebot import get_plugin_config
from nonebot.adapters import Event
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import At, UniMessage, on_alconna

from .config import Config
from .database import UserInfo, get_user, update_user
from .model import UserStatus, UserStatusExtra
from .util import (
    get_mc_body,
    get_mc_info,
    get_mc_server_status,
    manage_mc_banned_player,
    manage_mc_whitelist,
)

config = get_plugin_config(Config)


def group_enabled(event: Event) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False

    session_id = event.get_session_id().split("_")

    return int(session_id[1]) in config.MC_PLUGIN_ENABLE_GROUP


async def is_admin(event: Event) -> bool:
    try:
        user_id = event.get_user_id()
    except ValueError:
        return False

    user_info = await get_user(user_id)
    return (
        user_info.status_extra == UserStatusExtra.ADMIN.value
        if user_info
        else False
    )


alc_user = Alconna(
    "user",
    Subcommand(
        "bind",
        Args["username", str],
        alias={"绑定"},
    ),
    Subcommand(
        "unbind",
        alias={"解绑"},
    ),
    Subcommand(
        "sponsor",
        alias={"赞助"},
    ),
    Subcommand(
        "status",
        Args["target", At, None],
        alias={"状态"},
    ),
)

alc_server = Alconna(
    "server",
    Subcommand(
        "status",
        alias={"状态"},
    ),
)

alc_admin = Alconna(
    "admin",
    Subcommand(
        "ban",
        Args["target", At],
        Args["reason", StrMulti],
        alias={"封禁"},
    ),
    Subcommand(
        "unban",
        Args["target", At],
        alias={"解封"},
    ),
    Subcommand(
        "credits",
        Args["target", At],
        Args["number", int],
        alias={"点数"},
    ),
    Subcommand(
        "record",
        Args["target", At],
        Args["reason", StrMulti],
        alias={"记录"},
    ),
    Subcommand(
        "clear",
        Args["target", At],
        alias={"清空"},
    ),
    Subcommand(
        "add",
        Args["target", At],
        alias={"添加"},
    ),
    Subcommand(
        "remove",
        Args["target", At],
        alias={"移除"},
    ),
)

alc_whitelist = Alconna(
    "whitelist",
    Subcommand(
        "add",
        Args["username", str],
        alias={"添加"},
    ),
    Subcommand(
        "remove",
        Args["username", str],
        alias={"移除"},
    ),
)

user = on_alconna(
    alc_user,
    aliases={"用户"},
    rule=group_enabled,
)
server = on_alconna(
    alc_server,
    aliases={"服务器"},
    rule=group_enabled,
)
admin = on_alconna(
    alc_admin,
    aliases={"管理"},
    permission=SUPERUSER | is_admin,
    rule=group_enabled,
)

whitelist = on_alconna(
    alc_whitelist,
    aliases={"白名单"},
    permission=SUPERUSER | is_admin,
    rule=group_enabled,
)


@user.assign("bind")
async def user_bind(event: Event, username: str) -> None:
    user_id = event.get_user_id()

    try:
        mc_user = await get_mc_info(username)
        mc_body = await get_mc_body(username)

        user_info = UserInfo(
            qqid=user_id,
            username=mc_user.name,
            uuid=mc_user.uuid,
            status=UserStatus.BIND.value,
            status_extra=UserStatusExtra.NORMAL.value,
        )
        await update_user(user_info)

        results = manage_mc_whitelist(
            username,
            config.MC_SERVER_RCON,
            "add",
        )
        await UniMessage.text(
            "\n".join(f"{result[0]}: {result[1]}" for result in results)
        ).send()

    except Exception as e:
        await UniMessage.at(user_id).text(f"绑定失败: {e}").send()
        raise

    await UniMessage.at(user_id).image(raw=mc_body).text("绑定成功").finish()


@user.assign("unbind")
async def user_unbind(event: Event) -> None:
    user_id = event.get_user_id()

    try:
        user_info = await get_user(user_id)

        if not user_info:
            await UniMessage.at(user_id).text("当前未绑定MC账号").finish()
        else:
            results = manage_mc_whitelist(
                user_info.username,
                config.MC_SERVER_RCON,
                "remove",
            )
            await UniMessage.text(
                "\n".join(f"{result[0]}: {result[1]}" for result in results)
            ).send()

            user_info.status = UserStatus.UNBIND.value

            await update_user(user_info)

    except Exception as e:
        await UniMessage.at(user_id).text(f"解绑失败: {e}").send()
        raise

    await UniMessage.at(user_id).text(" 解绑成功").finish()


@user.assign("sponsor")
async def user_sponsor() -> None:
    await UniMessage.text("赞助功能正在开发中").finish()


@user.assign("status")
async def user_status(event: Event, target: At | None) -> None:
    user_id: str = str(target.target) if target else event.get_user_id()

    user_info = await get_user(user_id)

    if user_info:
        text = ""
        text += f"MC用户名: {user_info.username}\n"
        text += f"状态: {user_info.status}\n"
        if (target and target.target in config.SUPERUSERS) or (
            not target and user_id in config.SUPERUSERS
        ):
            text += "信息: 超级用户\n"
        elif target is not None and target.target not in config.SUPERUSERS:
            text += f"信息: {user_info.status_extra}\n"
        else:
            text += "信息: 无\n"
        text += f"点数: {user_info.credits}\n"
        if user_info.status == UserStatus.BANNED.value:
            text += f"封禁原因: {user_info.reason}\n"
        if user_info.reason_extra:
            text += "记录: \n"
        for reason in user_info.reason_extra:
            text += f"- {reason}\n"

        await UniMessage.text(text).finish()
    else:
        await UniMessage.text("当前未绑定MC账号").finish()


@server.assign("status")
async def server_status() -> None:
    message_list = []

    for mc_server in config.MC_SERVER:
        server_name = mc_server.split("|")[0]
        mc_server_status = await get_mc_server_status(mc_server.split("|")[1])
        if mc_server_status["online"]:
            message_list.append(
                f"[{server_name}]: 在线 - {mc_server_status['players']['online']}人"
            )
        else:
            message_list.append(f"[{server_name}]: 离线")

    await UniMessage.text("\n".join(message_list)).finish()


@admin.assign("ban")
async def ban_user(target: At, reason: str) -> None:
    user_info = await get_user(target.target)

    if not user_info:
        await UniMessage.text("用户未绑定MC账号").finish()
    else:
        results = manage_mc_banned_player(
            user_info.username,
            config.MC_SERVER_RCON,
            "ban",
            reason,
        )
        await UniMessage.text(
            "\n".join(f"{result[0]}: {result[1]}" for result in results)
        ).send()

        await update_user(user_info)
        await UniMessage.text("封禁成功").finish()


@admin.assign("unban")
async def unban_user(target: At) -> None:
    user_info = await get_user(target.target)

    if not user_info:
        await UniMessage.text("用户未绑定MC账号").finish()
    else:
        results = manage_mc_banned_player(
            user_info.username,
            config.MC_SERVER_RCON,
            "unban",
        )
        await UniMessage.text(
            "\n".join(f"{result[0]}: {result[1]}" for result in results)
        ).send()

        await update_user(user_info)
        await UniMessage.text("解封成功").finish()


@admin.assign("credits")
async def credits_user(target: At, number: int) -> None:
    user_info = await get_user(target.target)
    if user_info:
        user_info.credits = number
        await update_user(user_info)
        await UniMessage.text("点数修改成功").finish()
    else:
        await UniMessage.text("用户未绑定MC账号").finish()


@admin.assign("record")
async def record_user(target: At, reason: str) -> None:
    user_info = await get_user(target.target)
    datetime_now = datetime.now(tz=timezone(timedelta(hours=8)))
    if user_info:
        user_info.reason_extra.append(
            f"[{datetime_now.strftime('%Y-%m-%d %H:%M:%S')}] {reason}"
        )
        await update_user(user_info)
        await UniMessage.text("记录添加成功").finish()
    else:
        await UniMessage.text("用户未绑定MC账号").finish()


@admin.assign("clear")
async def clear_user(target: At) -> None:
    user_info = await get_user(target.target)
    if user_info:
        user_info.reason_extra = []
        await update_user(user_info)
        await UniMessage.text("记录清空成功").finish()
    else:
        await UniMessage.text("用户未绑定MC账号").finish()


@admin.assign("add")
async def add_user(target: At) -> None:
    user_info = await get_user(target.target)
    if user_info:
        user_info.status_extra = UserStatusExtra.ADMIN.value
        await update_user(user_info)
        await UniMessage.text("添加成功").finish()
    else:
        await UniMessage.text("用户未绑定MC账号").finish()


@admin.assign("remove")
async def remove_user(target: At) -> None:
    user_info = await get_user(target.target)
    if user_info:
        user_info.status_extra = UserStatusExtra.NORMAL.value
        await update_user(user_info)
        await UniMessage.text("移除成功").finish()
    else:
        await UniMessage.text("用户未绑定MC账号").finish()


@whitelist.assign("add")
async def whitelist_add(username: str) -> None:
    results = manage_mc_whitelist(
        username,
        config.MC_SERVER_RCON,
        "add",
    )
    await UniMessage.text(
        "\n".join(f"{result[0]}: {result[1]}" for result in results)
    ).send()

    await UniMessage.text("添加成功").finish()


@whitelist.assign("remove")
async def whitelist_remove(username: str) -> None:
    results = manage_mc_whitelist(
        username,
        config.MC_SERVER_RCON,
        "remove",
    )
    await UniMessage.text(
        "\n".join(f"{result[0]}: {result[1]}" for result in results)
    ).send()

    await UniMessage.text("移除成功").finish()

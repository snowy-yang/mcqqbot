from typing import Any

from httpx import AsyncClient
from mcrcon import MCRcon
from tenacity import retry, stop_after_attempt, wait_exponential

from .model import MCUser

ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"  # noqa: E501


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
)
async def get_mc_info(mc_name: str) -> MCUser:
    async with AsyncClient(headers={"User-Agent": ua}) as client:
        response = await client.get(
            f"https://api.mojang.com/users/profiles/minecraft/{mc_name}"
        )
        response.raise_for_status()
        resp = response.json()

    return MCUser(uuid=resp["id"], name=resp["name"])


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
)
async def get_mc_body(mc_name: str) -> bytes:
    async with AsyncClient(headers={"User-Agent": ua}) as client:
        response = await client.get(f"https://mc-heads.net/body/{mc_name}/right")
        response.raise_for_status()
        return response.content


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
)
async def get_mc_server_status(server_address: str) -> dict[str, Any]:
    async with AsyncClient(headers={"User-Agent": ua}) as client:
        response = await client.get(
            f"https://api.mcstatus.io/v2/status/java/{server_address}"
        )
        response.raise_for_status()
        return response.json()


def _parse_server_config(server: str) -> tuple[str, str, int, str]:
    """解析服务器配置字符串

    Args:
        server: 格式为 "name|address|password" 的字符串，其中 address 为 "host:port"

    Returns:
        (host, port, password) 元组
    """
    name = server.split("|", 2)[0]
    address = server.split("|", 2)[1]
    host = address.split(":", 1)[0]
    port = address.split(":", 1)[1]
    password = server.split("|", 2)[2]
    return name, host, int(port), password


def _execute_rcon_command(
    server_list: list[str], command: str
) -> list[tuple[str, str]]:
    """执行rcon命令的内部实现

    Args:
        server_list: 服务器配置列表
        command: 要执行的rcon命令

    Returns:
        包含(服务器名称, 是否成功)元组的列表
    """
    results = []

    for server in server_list:
        name, host, port, password = _parse_server_config(server)
        try:
            mcr = MCRcon(host, password, port)
            mcr.connect()
            result = mcr.command(command)
            mcr.disconnect()
            results.append((name, result))
        except ConnectionRefusedError:
            results.append((name, ""))

    return results


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
)
def manage_mc_whitelist(
    username: str, server_list: list[str], action: str
) -> list[tuple[str, str]]:
    """管理服务器白名单的内部实现

    Args:
        username: Minecraft用户名
        server_list: 服务器配置列表
        action: 操作类型，"add" 或 "remove"

    Returns:
        包含(服务器名称, 是否成功)元组的列表
    """
    command = f"whitelist {action} {username}"

    return _execute_rcon_command(server_list, command)


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
)
def manage_mc_banned_player(
    username: str, server_list: list[str], action: str, reason: str = ""
) -> list[tuple[str, str]]:
    """管理服务器黑名单的内部实现

    Args:
        username: Minecraft用户名
        server_list: 服务器配置列表
        action: 操作类型，"ban" 或 "unban"
        reason: 封禁原因

    Returns:
        包含(服务器名称, 是否成功)元组的列表
    """
    command = f"{action} {username} {reason if action == 'ban' else ''}"

    return _execute_rcon_command(server_list, command)

from enum import Enum

from pydantic import BaseModel


class UserStatus(Enum):
    UNBIND = "未绑定"
    BIND = "已绑定"
    BANNED = "已封禁"


class UserStatusExtra(Enum):
    NORMAL = "普通成员"
    VERIFIED = "已验证成员"
    ADMIN = "管理员"


class MCUser(BaseModel):
    uuid: str
    name: str

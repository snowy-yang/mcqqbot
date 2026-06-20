from pydantic import BaseModel


class Config(BaseModel):
    MC_PLUGIN_ENABLE_GROUP: list[int]
    SUPERUSERS: list[str]
    MC_SERVER: list[str]
    MC_SERVER_RCON: list[str]

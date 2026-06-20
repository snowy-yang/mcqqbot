from collections.abc import Sequence

from nonebot_plugin_orm import Model, get_session
from sqlalchemy import JSON, TEXT, Integer, select
from sqlalchemy.orm import Mapped, mapped_column


class UserInfo(Model):
    __tablename__ = "user"

    qqid: Mapped[str] = mapped_column(TEXT, primary_key=True)
    username: Mapped[str] = mapped_column(TEXT, nullable=False)
    uuid: Mapped[str] = mapped_column(TEXT, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(TEXT, nullable=False)
    status_extra: Mapped[str] = mapped_column(TEXT, nullable=False)
    reason: Mapped[str | None] = mapped_column(TEXT, nullable=False, default="")
    reason_extra: Mapped[list[str | None]] = mapped_column(
        JSON, nullable=False, default=[]
    )
    credits: Mapped[int | None] = mapped_column(Integer, nullable=False, default=0)


async def update_user(user: UserInfo) -> UserInfo:
    session = get_session()

    async with session:
        user_ = await session.merge(user)
        await session.commit()
        await session.refresh(user_)
        return user_


async def get_user(
    qqid: str,
) -> UserInfo | None:
    session = get_session()
    async with session:
        stmt = select(UserInfo).where(UserInfo.qqid == qqid)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

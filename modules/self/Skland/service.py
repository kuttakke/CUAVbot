from typing import Any

from sqlmodel import select

from .entity import AttendanceLog, User, db


async def add_user(user: User):
    await db.add(User, values=user.dict())


async def get_user_by_qq(qq: int) -> list[User]:
    return await db.select(select(User).where(User.qid == qq))


async def get_all_user() -> list[User]:
    return await db.select(select(User))


async def get_user_by_uid(uid: int) -> User | None:
    return await db.select_one(select(User).where(User.uid == uid))


async def update_user_by_uid(uid: int, data: dict[str, Any]):
    await db.update(User, data, [User.uid == uid])


async def add_attendance_log(attendance_log: AttendanceLog):
    await db.add(AttendanceLog, values=attendance_log.dict())


async def get_log_by_qq(qq: int) -> list[AttendanceLog]:
    return await db.select(select(AttendanceLog).where(AttendanceLog.qid == qq))

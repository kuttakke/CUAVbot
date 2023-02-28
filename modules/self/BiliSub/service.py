from datetime import datetime
from typing import Literal, Optional

from sqlalchemy.orm import selectinload
from sqlmodel import select

from .entity import DynamicLog, Subscription, db


async def get_dynamic_log_by_id(
    id: int, load_img: bool = False
) -> Optional[DynamicLog]:
    if load_img:
        return (
            await db.execute(
                select(DynamicLog)
                .options(selectinload(DynamicLog.imgs))
                .where(DynamicLog.id == id)
            )
        ).one_or_none()
    return await db.select_one(DynamicLog, [DynamicLog.id == id])


async def add_dynamic_log(log: DynamicLog):
    await db.add(DynamicLog, values=log.dict())


async def is_updated_dynamic(id: int) -> bool:
    return bool(await get_dynamic_log_by_id(id))


async def get_subscription(
    group: int, target: int, sub_type: Literal["dynamic", "live"]
) -> Optional[Subscription]:
    return await db.select_one(
        Subscription,
        [
            Subscription.group == group,
            Subscription.target == target,
            Subscription.sub_type == sub_type,
        ],
    )


async def get_subscription_by_group(group: int) -> list[Subscription]:
    return await db.select(Subscription, [Subscription.group == group])


async def get_sub_group(
    target: int, sub_type: Literal["dynamic", "live"] = "dynamic"
) -> list[int]:
    return [
        i.group
        for i in await db.select(
            Subscription,
            [Subscription.target == target, Subscription.sub_type == sub_type],
        )
    ]


async def is_subscribed(
    group: int, target: int, sub_type: Literal["dynamic", "live"]
) -> bool:
    return bool(await get_subscription(group, target, sub_type))


async def get_all_subscription() -> list[Subscription]:
    return await db.select(select(Subscription))


async def add_subscription(
    group: int, target: int, sub_type: Literal["dynamic", "live"] = "dynamic"
) -> Subscription:
    return await db.add(
        Subscription,
        values={
            "group": group,
            "target": target,
            "sub_type": sub_type,
            "create_time": datetime.now(),
        },
    )


async def remove_subscription(
    group: int, target: int, sub_type: Literal["dynamic", "live"] = "dynamic"
):
    await db.delete(
        Subscription,
        [
            Subscription.group == group,
            Subscription.target == target,
            Subscription.sub_type == sub_type,
        ],
    )

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User


class AccessMiddleware(BaseMiddleware):
    """Молча игнорирует апдейты от пользователей не из белого списка."""

    def __init__(self, allowed_users: frozenset[int]) -> None:
        self.allowed_users = allowed_users

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not self.allowed_users:
            return await handler(event, data)
        user: User | None = data.get("event_from_user")
        if user is None or user.id not in self.allowed_users:
            return None
        return await handler(event, data)

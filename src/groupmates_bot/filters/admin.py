from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject, User


class IsAdmin(BaseFilter):
    """Пропускает только пользователей из ADMIN_USERS (передаются в диспетчер как admin_users)."""

    async def __call__(
        self,
        event: TelegramObject,
        event_from_user: User | None = None,
        admin_users: frozenset[int] = frozenset(),
    ) -> bool:
        return event_from_user is not None and event_from_user.id in admin_users

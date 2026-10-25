from aiogram import Router

from groupmates_bot.handlers import admin, common, folders, photos


def setup_routers() -> Router:
    # Роутеры создаются заново на каждый вызов, чтобы диспетчеров можно было
    # собрать несколько (например, в тестах). common последним: в нём fallback.
    router = Router()
    router.include_routers(
        admin.create_router(),
        folders.create_router(),
        photos.create_router(),
        common.create_router(),
    )
    return router

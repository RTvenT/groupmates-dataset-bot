from aiogram import Router

from groupmates_bot.handlers import common, folders, photos


def setup_routers() -> Router:
    router = Router()
    # common последним: в нём fallback на любой текст
    router.include_routers(folders.router, photos.router, common.router)
    return router

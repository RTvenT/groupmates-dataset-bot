from aiogram.fsm.state import State, StatesGroup


class FolderStates(StatesGroup):
    waiting_for_name = State()

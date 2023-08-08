import asyncio

from src.register import Registrator


def start():
    """Функция запуска скрипта"""

    registrator = Registrator()
    asyncio.run(registrator.register())


if __name__ == "__main__":
    start()

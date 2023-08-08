from src.register import Registrator
import asyncio


def start_register():
    registrator = Registrator()
    asyncio.run(registrator.register())


if __name__ == "__main__":
    start_register()

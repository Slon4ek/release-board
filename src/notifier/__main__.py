import asyncio
import logging

from src.config import settings
from src.notifier.handler import broker


async def amain() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    await broker.start()
    try:
        logging.getLogger("notifier").info("notifier started, topic=%s group=notifier", settings.RELAY_TOPIC)
        await asyncio.Event().wait()
    finally:
        await broker.stop()


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Ctrl+C")

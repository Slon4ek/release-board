import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from faststream.confluent import KafkaBroker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import async_session_maker
from src.models import OutboxEvent

logger = logging.getLogger(__name__)


def _build_message(event: OutboxEvent) -> dict[str, Any]:
    return {
        "event_id": str(event.id),
        "event_type": event.event_type,
        "occurred_at": event.created_at.isoformat(),
        "schema_version": 1,
        "aggregate_id": str(event.aggregate_id),
        "payload": event.payload,
    }


async def _fetch_batch(session: AsyncSession) -> list[OutboxEvent]:
    stmt = (
        select(OutboxEvent)
        .where(OutboxEvent.published_at.is_(None))
        .order_by(OutboxEvent.created_at)
        .limit(settings.RELAY_BATCH_SIZE)
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


class Relay:
    def __init__(self) -> None:
        self._broker = KafkaBroker(settings.KAFKA_BOOTSTRAP_SERVERS)

    async def run_forever(self) -> None:
        async with self._broker:
            logger.info("relay started, bootstrap=%s", settings.KAFKA_BOOTSTRAP_SERVERS)
            while True:
                try:
                    published = await self.publish_batch()
                except Exception:
                    logger.exception("relay iteration failed")
                    await asyncio.sleep(settings.RELAY_POLL_INTERVAL_SEC)
                    continue
                if published == 0:
                    await asyncio.sleep(settings.RELAY_POLL_INTERVAL_SEC)

    async def publish_batch(self) -> int:
        async with async_session_maker() as session:
            events = await _fetch_batch(session)
            published = 0
            for event in events:
                await self._broker.publish(
                    message=_build_message(event),
                    topic=settings.RELAY_TOPIC,
                    key=str(event.aggregate_id).encode(),
                )
                event.published_at = datetime.now(UTC)
                event.attempts += 1
                published += 1
            await session.commit()
            return published

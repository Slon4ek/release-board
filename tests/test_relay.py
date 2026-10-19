"""Тесты relay: publish_batch через TestKafkaBroker — без живой Kafka."""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import pytest
from faststream.confluent import TestKafkaBroker

from src.config import settings
from src.models import OutboxEvent
from src.relay.poller import Relay


@pytest.fixture
async def relay_with_sink() -> AsyncGenerator[tuple[Relay, Any], None]:
    relay = Relay()

    @relay._broker.subscriber(settings.RELAY_TOPIC, group_id="test-relay")
    async def relay_sink(message: Any) -> None:
        """Приёмник relay-сообщений в тесте (loopback FakeProducer)."""

    yield relay, relay_sink


async def test_publish_batch_publishes_and_marks(db_session, relay_with_sink) -> None:
    """Одна необработанная строка: опубликована, published_at/attempts заполнены, формат сообщения верен."""
    relay, relay_sink = relay_with_sink
    aggregate_id = uuid.uuid4()
    row = OutboxEvent(
        aggregate_id=aggregate_id,
        event_type="release.created",
        payload={"service": "billing", "version": "1.0.0", "environment": "stage", "status": "planned"},
    )
    db_session.add(row)
    await db_session.commit()

    async with TestKafkaBroker(relay._broker):
        published = await relay.publish_batch()
        relay_sink.mock.assert_called_once()
        body = relay_sink.mock.call_args.args[0]

    assert published == 1
    assert body["event_id"] == str(row.id)
    assert body["event_type"] == "release.created"
    assert body["aggregate_id"] == str(aggregate_id)
    assert body["schema_version"] == 1
    assert body["payload"]["service"] == "billing"

    await db_session.refresh(row)
    assert row.published_at is not None
    assert row.attempts == 1


async def test_publish_batch_skips_already_published(db_session, relay_with_sink) -> None:
    """Строка с published_at пропускается: работает WHERE published_at IS NULL."""
    relay, relay_sink = relay_with_sink
    db_session.add(
        OutboxEvent(
            aggregate_id=uuid.uuid4(),
            event_type="release.created",
            payload={"service": "x", "version": "1.0.0", "environment": "stage", "status": "planned"},
            published_at=datetime.now(UTC),
        )
    )
    await db_session.commit()

    async with TestKafkaBroker(relay._broker):
        published = await relay.publish_batch()
        relay_sink.mock.assert_not_called()

    assert published == 0


async def test_publish_batch_empty_outbox(relay_with_sink) -> None:
    """Пустой outbox: ноль публикаций, ничего не падает."""
    relay, relay_sink = relay_with_sink

    async with TestKafkaBroker(relay._broker):
        published = await relay.publish_batch()
        relay_sink.mock.assert_not_called()

    assert published == 0

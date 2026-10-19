"""Тесты notifier: идемпотентность, DLQ-путь, оба типа событий — через TestKafkaBroker."""

import uuid
from typing import Any
from unittest.mock import MagicMock

from faststream.confluent import TestKafkaBroker
from sqlalchemy import func, select

from src.config import settings
from src.events import (
    EventType,
    ReleaseCreated,
    ReleaseCreatedPayload,
    ReleaseStatusChanged,
    ReleaseStatusChangedPayload,
)
from src.models import ProcessedEvent
from src.notifier.handler import broker, handle_event


@broker.subscriber(settings.DLQ_TOPIC, group_id="test-dlq")
async def dlq_sink(message: Any) -> None:
    """Приёмник DLQ в тесте: FakeProducer роутит publish() сюда (loopback)."""


def _release_created() -> ReleaseCreated:
    return ReleaseCreated(
        event_type=EventType.RELEASE_CREATED,
        aggregate_id=uuid.uuid4(),
        payload=ReleaseCreatedPayload(
            service="billing",
            version="1.2.3",
            environment="stage",
            status="planned",
        ),
    )


def _release_status_changed() -> ReleaseStatusChanged:
    return ReleaseStatusChanged(
        event_type=EventType.RELEASE_STATUS_CHANGED,
        aggregate_id=uuid.uuid4(),
        payload=ReleaseStatusChangedPayload(
            service="billing",
            version="1.4.0",
            environment="stage",
            previous_status="planned",
            new_status="deployed",
        ),
    )


async def _count_processed(db_session) -> int:
    result = await db_session.execute(select(func.count()).select_from(ProcessedEvent))
    return int(result.scalar_one())


async def test_valid_created_is_processed(db_session, monkeypatch) -> None:
    """Валидное release.created: строка в processed_events, _notify ровно один раз, в DLQ не уходит."""
    notify = MagicMock()
    monkeypatch.setattr("src.notifier.handler._notify", notify)
    event = _release_created()

    async with TestKafkaBroker(broker):
        await broker.publish(event.model_dump(mode="json"), topic=settings.RELAY_TOPIC)

        handle_event.mock.assert_called_once()
        notify.assert_called_once()
        assert notify.call_args.args[0].event_id == event.event_id
        dlq_sink.mock.assert_not_called()

    assert await db_session.get(ProcessedEvent, event.event_id) is not None
    assert await _count_processed(db_session) == 1


async def test_duplicate_is_skipped(db_session, monkeypatch) -> None:
    """Повторное событие: запись уже есть → _notify не вызывается, строка не дублируется."""
    notify = MagicMock()
    monkeypatch.setattr("src.notifier.handler._notify", notify)
    event = _release_created()
    db_session.add(ProcessedEvent(event_id=event.event_id))
    await db_session.commit()

    async with TestKafkaBroker(broker):
        await broker.publish(event.model_dump(mode="json"), topic=settings.RELAY_TOPIC)

        notify.assert_not_called()
        dlq_sink.mock.assert_not_called()

    assert await _count_processed(db_session) == 1


async def test_invalid_event_goes_to_dlq(db_session, monkeypatch) -> None:
    """Кривое сообщение: уходит в DLQ с original/error/failed_at, в processed_events не попадает."""
    notify = MagicMock()
    monkeypatch.setattr("src.notifier.handler._notify", notify)

    async with TestKafkaBroker(broker):
        await broker.publish({"hello": 1}, topic=settings.RELAY_TOPIC)

        notify.assert_not_called()
        dlq_sink.mock.assert_called_once()
        payload = dlq_sink.mock.call_args.args[0]

    assert payload["original"] == {"hello": 1}
    assert "validation error" in payload["error"]
    assert payload["failed_at"]
    assert await _count_processed(db_session) == 0


async def test_status_changed_is_processed(db_session, monkeypatch) -> None:
    """Вторая ветка discriminated union: release.status_changed тоже обрабатывается."""
    notify = MagicMock()
    monkeypatch.setattr("src.notifier.handler._notify", notify)
    event = _release_status_changed()

    async with TestKafkaBroker(broker):
        await broker.publish(event.model_dump(mode="json"), topic=settings.RELAY_TOPIC)

        notify.assert_called_once()
        assert notify.call_args.args[0].event_type == "release.status_changed"
        dlq_sink.mock.assert_not_called()

    assert await db_session.get(ProcessedEvent, event.event_id) is not None

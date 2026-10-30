import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from faststream.confluent import KafkaBroker
from faststream.middlewares import AckPolicy
from pydantic import Field, TypeAdapter, ValidationError
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.config import settings
from src.database import async_session_maker
from src.events import ReleaseCreated, ReleaseStatusChanged
from src.models import ProcessedEvent

logger = logging.getLogger(__name__)

broker = KafkaBroker(settings.KAFKA_BOOTSTRAP_SERVERS, allow_auto_create_topics=False)

AnyEvent = Annotated[ReleaseCreated | ReleaseStatusChanged, Field(discriminator="event_type")]
_event_adapter: TypeAdapter[AnyEvent] = TypeAdapter(AnyEvent)
_retries: dict[str, int] = {}


async def _safe_decode(message: Any) -> Any:
    body = getattr(message, "body", message)
    if isinstance(body, (bytes, bytearray)):
        try:
            return json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
            return body
    return body


async def _send_to_dlq(message: Any, reason: str) -> None:
    await broker.publish(
        message={
            "original": message,
            "error": reason,
            "failed_at": datetime.now(UTC).isoformat(),
        },
        topic=settings.DLQ_TOPIC,
    )


@broker.subscriber(
    settings.RELAY_TOPIC,
    group_id="notifier",
    auto_offset_reset="earliest",
    ack_policy=AckPolicy.NACK_ON_ERROR,
    decoder=_safe_decode,
)
async def handle_event(message: Any) -> None:
    if isinstance(message, (bytes, bytearray)):
        logger.error("invalid event -> dlq: %s", message)
        await _send_to_dlq(message, reason="invalid JSON body")
        return
    try:
        event = _event_adapter.validate_python(message)
    except ValidationError as exc:
        logger.error("invalid event -> dlq: %s", exc)
        await _send_to_dlq(message, reason=str(exc))
        return

    _MAX_RETRIES = 5

    key = str(event.event_id)
    try:
        async with async_session_maker() as session:
            insert_result = await session.execute(
                pg_insert(ProcessedEvent)
                .values(event_id=event.event_id)
                .on_conflict_do_nothing()
                .returning(ProcessedEvent.event_id)
            )
            if insert_result.scalar_one_or_none() is None:
                logger.info("duplicate event %s, skipped", event.event_id)
                return

            _notify(event)
            await session.commit()
            _retries.pop(key, None)
    except Exception:
        attempts = _retries.get(key, 0) + 1
        _retries[key] = attempts
        if attempts < _MAX_RETRIES:
            delay = min(2**attempts, 30)
            logger.warning("processing failed (attempt %d/%d), retry in %ds", attempts, _MAX_RETRIES, delay)
            await asyncio.sleep(delay)
            raise  # → NACK: позиция возвращается к сообщению, оно перечитается
        logger.exception("processing failed %d times -> dlq", attempts)
        await _send_to_dlq(message, reason=f"processing failed after {attempts} attempts (see logs)")
        _retries.pop(key, None)
        # выход без исключения → подтверждение: поток движется, событие сохранено в DLQ


def _notify(event: ReleaseCreated | ReleaseStatusChanged) -> None:
    match event:
        case ReleaseCreated(payload=payload):
            logger.info(
                "NOTIFY: created release %s %s for %s (%s)",
                payload.service,
                payload.version,
                payload.environment,
                event.aggregate_id,
            )
        case ReleaseStatusChanged(payload=payload):
            logger.info(
                "NOTIFY: release %s %s %s -> %s",
                payload.service,
                payload.version,
                payload.previous_status,
                payload.new_status,
            )

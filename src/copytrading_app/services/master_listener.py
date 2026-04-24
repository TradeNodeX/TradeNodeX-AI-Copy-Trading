from __future__ import annotations

from datetime import timedelta

from copytrading_app.domain.types import MasterEventPayload, utc_now
from copytrading_app.schemas.api import MasterEventIn
from copytrading_app.services.orchestrator import Orchestrator


class MasterListenerService:
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator

    async def ingest_event(self, event: MasterEventIn):
        payload = MasterEventPayload(
            source_exchange=event.source_exchange,
            source_account=event.source_account,
            source_order_or_fill_id=event.source_order_or_fill_id,
            symbol=event.symbol,
            previous_position_qty=event.previous_position_qty,
            current_position_qty=event.current_position_qty,
            price=event.price,
            event_time=event.event_time or utc_now(),
            payload=event.payload,
        )
        return await self.orchestrator.handle_master_event(payload)

    async def snapshot_due(self, last_snapshot_at) -> bool:
        if last_snapshot_at is None:
            return True
        return utc_now() - last_snapshot_at >= timedelta(seconds=10)


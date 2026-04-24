from __future__ import annotations

from decimal import Decimal

from copytrading_app.domain.enums import PositionSide, SignalAction
from copytrading_app.domain.types import MasterEventPayload, NormalizedSignalPayload


class SignalNormalizer:
    def build_signal(
        self,
        signal_source_id: str,
        master_event_id: str,
        payload: MasterEventPayload,
        idempotency_key: str,
    ) -> NormalizedSignalPayload:
        action = self._resolve_action(payload.previous_position_qty, payload.current_position_qty)
        target_side = self._resolve_side(payload.current_position_qty)
        return NormalizedSignalPayload(
            signal_source_id=signal_source_id,
            master_event_id=master_event_id,
            source_exchange=payload.source_exchange,
            source_account=payload.source_account,
            symbol=payload.symbol,
            action=action,
            target_side=target_side,
            target_quantity=payload.current_position_qty.copy_abs(),
            delta_quantity=payload.current_position_qty - payload.previous_position_qty,
            idempotency_key=idempotency_key,
        )

    def _resolve_side(self, quantity: Decimal) -> PositionSide:
        if quantity > 0:
            return PositionSide.LONG
        if quantity < 0:
            return PositionSide.SHORT
        return PositionSide.FLAT

    def _resolve_action(self, previous: Decimal, current: Decimal) -> SignalAction:
        if previous == 0 and current != 0:
            return SignalAction.OPEN
        if previous != 0 and current == 0:
            return SignalAction.CLOSE
        if previous == 0 and current == 0:
            return SignalAction.SYNC_TO_TARGET_POSITION
        if (previous > 0 > current) or (previous < 0 < current):
            return SignalAction.FLIP
        if abs(current) > abs(previous):
            return SignalAction.INCREASE
        if abs(current) < abs(previous):
            return SignalAction.REDUCE
        return SignalAction.SYNC_TO_TARGET_POSITION


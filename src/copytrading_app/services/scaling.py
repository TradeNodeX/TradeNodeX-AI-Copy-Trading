from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from copytrading_app.domain.enums import CopyMode, PositionSide
from copytrading_app.domain.types import InstrumentConstraints


class ScalingService:
    def scale_target_quantity(
        self,
        master_target_quantity: Decimal,
        scale_factor: Decimal,
        constraints: InstrumentConstraints,
        copy_mode: CopyMode,
    ) -> Decimal:
        source_quantity = master_target_quantity if copy_mode == CopyMode.EXACT else master_target_quantity * scale_factor
        return self._normalize(source_quantity.copy_abs(), constraints)

    def scale_delta_quantity(
        self,
        master_delta_quantity: Decimal,
        scale_factor: Decimal,
        constraints: InstrumentConstraints,
        copy_mode: CopyMode,
    ) -> Decimal:
        source_quantity = master_delta_quantity if copy_mode == CopyMode.EXACT else master_delta_quantity * scale_factor
        sign = Decimal("1") if source_quantity >= 0 else Decimal("-1")
        return self._normalize(abs(source_quantity), constraints) * sign

    def resolve_side(self, target_quantity: Decimal) -> PositionSide:
        if target_quantity > 0:
            return PositionSide.LONG
        if target_quantity < 0:
            return PositionSide.SHORT
        return PositionSide.FLAT

    def _normalize(self, quantity: Decimal, constraints: InstrumentConstraints) -> Decimal:
        if quantity == 0:
            return Decimal("0")
        if quantity < constraints.min_quantity:
            return Decimal("0")
        steps = (quantity / constraints.quantity_step).to_integral_value(rounding=ROUND_DOWN)
        rounded = steps * constraints.quantity_step
        if rounded < constraints.min_quantity:
            return Decimal("0")
        return rounded


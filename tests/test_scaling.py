from decimal import Decimal

from copytrading_app.domain.enums import CopyMode
from copytrading_app.domain.types import InstrumentConstraints
from copytrading_app.services.scaling import ScalingService


def test_exact_copy_keeps_quantity_when_constraints_allow() -> None:
    service = ScalingService()
    constraints = InstrumentConstraints(symbol="BTCUSDT", quantity_step=Decimal("0.01"), min_quantity=Decimal("0.01"))

    result = service.scale_target_quantity(
        master_target_quantity=Decimal("1.23"),
        scale_factor=Decimal("0.5"),
        constraints=constraints,
        copy_mode=CopyMode.EXACT,
    )

    assert result == Decimal("1.23")


def test_scaled_copy_rounds_down_to_step() -> None:
    service = ScalingService()
    constraints = InstrumentConstraints(symbol="BTCUSDT", quantity_step=Decimal("0.01"), min_quantity=Decimal("0.01"))

    result = service.scale_target_quantity(
        master_target_quantity=Decimal("1.237"),
        scale_factor=Decimal("0.5"),
        constraints=constraints,
        copy_mode=CopyMode.SCALE,
    )

    assert result == Decimal("0.61")


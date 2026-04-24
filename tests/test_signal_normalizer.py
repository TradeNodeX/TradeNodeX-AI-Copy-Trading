from decimal import Decimal

from copytrading_app.domain.enums import Exchange, PositionSide, SignalAction
from copytrading_app.domain.types import MasterEventPayload
from copytrading_app.services.signal_normalizer import SignalNormalizer


def test_normalizer_marks_flip_and_delta() -> None:
    normalizer = SignalNormalizer()
    payload = MasterEventPayload(
        source_exchange=Exchange.BINANCE,
        source_account="master-a",
        source_order_or_fill_id="fill-1",
        symbol="BTCUSDT",
        previous_position_qty=Decimal("2"),
        current_position_qty=Decimal("-1"),
    )

    signal = normalizer.build_signal("source-1", "event-1", payload, "k")

    assert signal.action == SignalAction.FLIP
    assert signal.target_side == PositionSide.SHORT
    assert signal.target_quantity == Decimal("1")
    assert signal.delta_quantity == Decimal("-3")
    assert signal.signal_source_id == "source-1"


from __future__ import annotations

from copytrading_app.db.models import CopyTradeModel, FollowerAccountModel, SignalSourceModel
from copytrading_app.domain.enums import CopyMode, ValidationStatus


def validate_copy_trade(
    copy_trade: CopyTradeModel,
    follower: FollowerAccountModel,
    signal_source: SignalSourceModel,
) -> tuple[ValidationStatus, str | None, list[str]]:
    reasons: list[str] = []
    if follower.environment != signal_source.environment:
        reasons.append(f"FAILED: environment mismatch source={signal_source.environment} follower={follower.environment}.")
    else:
        reasons.append(f"OK: environment aligned at {signal_source.environment}.")
    if copy_trade.copy_mode == CopyMode.EXACT.value:
        if signal_source.default_leverage and follower.leverage and signal_source.default_leverage != follower.leverage:
            reasons.append(f"FAILED: EXACT 1:1 requires matching leverage source={signal_source.default_leverage} follower={follower.leverage}.")
        else:
            reasons.append("OK: EXACT 1:1 leverage check passed.")
        if signal_source.margin_mode != follower.margin_mode:
            reasons.append(f"FAILED: EXACT 1:1 requires matching margin mode source={signal_source.margin_mode} follower={follower.margin_mode}.")
        else:
            reasons.append(f"OK: margin mode aligned at {signal_source.margin_mode}.")
        if signal_source.hedge_mode != follower.hedge_mode:
            reasons.append(f"FAILED: EXACT 1:1 requires matching hedge mode source={signal_source.hedge_mode} follower={follower.hedge_mode}.")
        else:
            reasons.append(f"OK: hedge mode aligned at {signal_source.hedge_mode}.")
    else:
        reasons.append(f"OK: SCALE mode uses scale factor {copy_trade.scale_factor}.")
    failures = [item for item in reasons if item.startswith("FAILED:")]
    if failures:
        return ValidationStatus.FAILED, failures[0], reasons
    return ValidationStatus.VERIFIED, "Copy-trade consistency report passed.", reasons

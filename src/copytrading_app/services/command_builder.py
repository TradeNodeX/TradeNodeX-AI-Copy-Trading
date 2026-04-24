from __future__ import annotations

import json

from copytrading_app.domain.types import GeneratedCommand
from copytrading_app.schemas.api import CommandBuilderRequest


class CommandBuilderService:
    def build(self, request: CommandBuilderRequest) -> GeneratedCommand:
        quantity_mode_map = {
            "ABSOLUTE": "absolute",
            "PERCENT_AVAILABLE": "percentAvailableBalance",
            "PERCENT_WALLET": "percentWallet",
            "RISK_PERCENT": "riskPercent",
            "COPY_TRADER": "signalSource",
        }
        payload = {
            "commandName": request.name,
            "exchange": request.exchange.value,
            "environment": request.environment.value,
            "productType": request.product_type,
            "action": request.action.value,
            "symbol": request.symbol,
            "orderType": request.order_type.value.lower(),
            "unitsType": quantity_mode_map.get(request.quantity_mode.value, request.quantity_mode.value.lower()),
            "units": str(request.quantity_value) if request.quantity_value is not None else None,
            "leverage": request.leverage,
            "marginMode": request.margin_mode.value.lower(),
            "hedgeMode": request.hedge_mode,
            "broadcastTrade": request.broadcast_trade,
            "createCopyTradeSignal": request.create_copy_trade_signal,
            "signalSourceId": request.signal_source_id,
            "accountId": request.account_id,
            "source": request.signal_source_id,
            "limitPrice": str(request.limit_price) if request.limit_price is not None else None,
            "stopPrice": str(request.stop_price) if request.stop_price is not None else None,
            "stopLossPercent": str(request.stop_loss_percent) if request.stop_loss_percent is not None else None,
            "delaySeconds": request.delay_seconds,
            "useDca": request.use_dca,
            "useFixedSize": request.use_fixed_size,
            "useEntireBalance": request.use_entire_balance,
            "preventPyramiding": request.prevent_pyramiding,
            "closeCurrentPosition": request.close_current_position,
            "cancelPendingOrders": request.cancel_pending_orders,
            "conditionalPyramiding": request.conditional_pyramiding,
            "closeInProfitOnly": request.close_in_profit_only,
            "cancelAllOrders": request.cancel_all_orders,
            "cancelDcaOrders": request.cancel_dca_orders,
            "partialClose": request.partial_close,
            "closeByLimitOrder": request.close_by_limit_order,
            "closeAll": request.close_all,
            "closeLong": request.close_long,
            "closeShort": request.close_short,
            "targets": request.take_profit_steps,
        }
        raw_command = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return GeneratedCommand(
            exchange=request.exchange,
            environment=request.environment,
            action=request.action,
            symbol=request.symbol,
            order_type=request.order_type,
            quantity_mode=request.quantity_mode,
            quantity_value=request.quantity_value,
            leverage=request.leverage,
            margin_mode=request.margin_mode,
            hedge_mode=request.hedge_mode,
            broadcast_trade=request.broadcast_trade,
            create_copy_trade_signal=request.create_copy_trade_signal,
            signal_source_id=request.signal_source_id,
            account_id=request.account_id,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
            take_profit_steps=request.take_profit_steps,
            raw_command=raw_command,
        )

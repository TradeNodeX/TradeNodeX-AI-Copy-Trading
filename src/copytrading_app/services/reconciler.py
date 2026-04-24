from __future__ import annotations

from decimal import Decimal

from copytrading_app.domain.enums import CopyMode, Exchange, LogType, PositionSide, QueueName, ReconciliationStatus, SignalAction, SignalStatus
from copytrading_app.domain.types import ExecutionCommandPayload
from copytrading_app.repositories.execution_repository import ExecutionRepository
from copytrading_app.repositories.signal_repository import SignalRepository
from copytrading_app.services.exchanges.base import ExchangeClient
from copytrading_app.services.queues.base import TaskQueue
from copytrading_app.services.security import SecretCipher


class Reconciler:
    def __init__(
        self,
        signal_repository: SignalRepository,
        execution_repository: ExecutionRepository,
        exchange_clients: dict[Exchange, ExchangeClient],
        queue: TaskQueue,
        tolerance: Decimal,
        secret_cipher: SecretCipher,
    ):
        self.signal_repository = signal_repository
        self.execution_repository = execution_repository
        self.exchange_clients = exchange_clients
        self.queue = queue
        self.tolerance = tolerance
        self.secret_cipher = secret_cipher

    async def reconcile_signal(self, signal_id: str) -> list[str]:
        signal = await self.signal_repository.get_signal(signal_id)
        if signal is None:
            raise ValueError(f"signal {signal_id} not found")

        repair_task_ids: list[str] = []
        for task in signal.execution_tasks:
            account = task.follower_account
            if account is None:
                continue
            client = self.exchange_clients[Exchange(task.exchange)]
            api_key = await self.secret_cipher.decrypt(account.api_key_ciphertext)
            api_secret = await self.secret_cipher.decrypt(account.api_secret_ciphertext)
            api_passphrase = await self.secret_cipher.decrypt(account.api_passphrase_ciphertext)
            snapshot = await client.fetch_position(account, task.symbol, api_key, api_secret, api_passphrase)
            await self.execution_repository.save_position_snapshot(snapshot)
            expected_quantity = self._signed_target_quantity(PositionSide(task.target_side), Decimal(task.target_quantity))
            delta = expected_quantity - snapshot.quantity
            status = ReconciliationStatus.MATCHED if abs(delta) <= self.tolerance else ReconciliationStatus.OUT_OF_SYNC
            action_taken = None

            if status == ReconciliationStatus.OUT_OF_SYNC:
                repair_payload = ExecutionCommandPayload(
                    task_id=f"{task.id}-repair",
                    signal_id=signal.id,
                    signal_source_id=signal.signal_source_id,
                    copy_trade_id=task.copy_trade_id,
                    follower_account_id=task.follower_account_id,
                    exchange=Exchange(task.exchange),
                    symbol=task.symbol,
                    action=SignalAction(task.action),
                    target_side=PositionSide(task.target_side),
                    target_quantity=Decimal(task.target_quantity),
                    delta_quantity=delta,
                    copy_mode=CopyMode(task.copy_mode),
                    reduce_only=task.reduce_only,
                    queue_name=QueueName.RECOVERY,
                    message_group=task.message_group,
                    version=task.version + 1,
                    idempotency_key=f"{task.id}:repair:{task.version + 1}",
                )
                await self.execution_repository.create_task(repair_payload)
                await self.queue.publish(repair_payload)
                repair_task_ids.append(repair_payload.task_id)
                action_taken = QueueName.RECOVERY.value
                status = ReconciliationStatus.REPAIR_ENQUEUED

            await self.execution_repository.record_reconciliation(
                signal_id=signal.id,
                follower_account_id=task.follower_account_id,
                symbol=task.symbol,
                expected_quantity=expected_quantity,
                actual_quantity=snapshot.quantity,
                delta_quantity=delta,
                status=status,
                details=snapshot.model_dump(mode="json"),
                action_taken=action_taken,
            )

        await self.execution_repository.add_trade_log(
            exchange=signal.source_exchange,
            log_type=LogType.RECONCILE,
            log_key=signal.source_account,
            message=f"Reconciliation completed for signal {signal.id}. Repair tasks: {len(repair_task_ids)}",
            details={"signal_id": signal.id, "repair_task_ids": repair_task_ids},
        )
        await self.signal_repository.update_status(signal.id, SignalStatus.RECONCILED)
        return repair_task_ids

    def _signed_target_quantity(self, target_side: PositionSide, target_quantity: Decimal) -> Decimal:
        if target_side == PositionSide.SHORT:
            return -target_quantity
        if target_side == PositionSide.FLAT:
            return Decimal("0")
        return target_quantity

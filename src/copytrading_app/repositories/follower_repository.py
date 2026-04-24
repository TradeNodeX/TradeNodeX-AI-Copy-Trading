from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from copytrading_app.db.models import AccountSymbolRuleModel, FollowerAccountModel, OperatorActionModel
from copytrading_app.domain.enums import FollowerStatus, ValidationStatus
from copytrading_app.schemas.api import FollowerCreateRequest, SymbolRuleUpsertRequest


class FollowerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        request: FollowerCreateRequest,
        *,
        api_key_ciphertext: str | None,
        api_secret_ciphertext: str | None,
        api_passphrase_ciphertext: str | None,
    ) -> FollowerAccountModel:
        model = FollowerAccountModel(
            name=request.name,
            exchange=request.exchange.value,
            environment=request.environment.value,
            account_group=request.account_group,
            scale_factor=request.scale_factor,
            exact_copy_mode=request.exact_copy_mode,
            leverage=request.leverage,
            margin_mode=request.margin_mode.value,
            hedge_mode=request.hedge_mode,
            api_key_ciphertext=api_key_ciphertext or request.api_key_ciphertext,
            api_secret_ciphertext=api_secret_ciphertext or request.api_secret_ciphertext,
            api_passphrase_ciphertext=api_passphrase_ciphertext or request.api_passphrase_ciphertext,
            kms_key_id=request.kms_key_id,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def get(self, follower_id: str) -> FollowerAccountModel | None:
        query = self._with_rules().where(FollowerAccountModel.id == follower_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list(self) -> Sequence[FollowerAccountModel]:
        result = await self.session.execute(self._with_rules().order_by(FollowerAccountModel.created_at.desc()))
        return result.scalars().all()

    async def list_active(self) -> Sequence[FollowerAccountModel]:
        query = self._with_rules().where(FollowerAccountModel.status == FollowerStatus.ACTIVE.value)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_fields(self, follower_id: str, updates: dict) -> FollowerAccountModel | None:
        model = await self.get(follower_id)
        if model is None:
            return None
        for key, value in updates.items():
            setattr(model, key, value)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def delete(self, follower_id: str) -> bool:
        model = await self.get(follower_id)
        if model is None:
            return False
        await self.session.delete(model)
        await self.session.flush()
        return True

    async def set_status(self, follower_id: str, status: FollowerStatus) -> FollowerAccountModel | None:
        model = await self.get(follower_id)
        if model is None:
            return None
        model.status = status.value
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def update_validation(
        self,
        follower_id: str,
        validation_status: ValidationStatus,
        validation_message: str | None,
        *,
        credential_status: ValidationStatus | None = None,
        permission_status: ValidationStatus | None = None,
        connectivity_status: ValidationStatus | None = None,
        trading_ready_status: ValidationStatus | None = None,
        validation_reasons: list[str] | None = None,
    ) -> FollowerAccountModel | None:
        model = await self.get(follower_id)
        if model is None:
            return None
        model.validation_status = validation_status.value
        model.validation_message = validation_message
        model.credential_status = (credential_status or validation_status).value
        model.permission_status = (permission_status or validation_status).value
        model.connectivity_status = (connectivity_status or validation_status).value
        model.trading_ready_status = (trading_ready_status or validation_status).value
        model.validation_reasons = validation_reasons or ([validation_message] if validation_message else [])
        model.last_validated_at = model.updated_at
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def upsert_rule(self, follower_id: str, request: SymbolRuleUpsertRequest) -> AccountSymbolRuleModel:
        follower = await self.get(follower_id)
        if follower is None:
            raise ValueError(f"follower {follower_id} not found")

        existing = next((rule for rule in follower.symbol_rules if rule.symbol == request.symbol), None)
        if existing is None:
            existing = AccountSymbolRuleModel(
                follower_account_id=follower_id,
                symbol=request.symbol,
            )
            self.session.add(existing)

        existing.enabled = request.enabled
        existing.scale_factor = request.scale_factor
        existing.max_leverage = request.max_leverage
        existing.max_notional = request.max_notional
        existing.min_notional_override = request.min_notional_override
        await self.session.flush()
        await self.session.refresh(existing)
        return existing

    async def record_operator_action(
        self,
        operator: str,
        action: str,
        target_type: str,
        target_id: str,
        details: dict,
    ) -> None:
        self.session.add(
            OperatorActionModel(
                operator=operator,
                action=action,
                target_type=target_type,
                target_id=target_id,
                details=details,
            )
        )
        await self.session.flush()

    def _with_rules(self) -> Select[tuple[FollowerAccountModel]]:
        return select(FollowerAccountModel).options(selectinload(FollowerAccountModel.symbol_rules))


def resolve_effective_scale(default_scale: Decimal, rule: AccountSymbolRuleModel | None) -> Decimal:
    if rule and rule.scale_factor is not None:
        return Decimal(rule.scale_factor)
    return Decimal(default_scale)

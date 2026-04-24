from __future__ import annotations

import asyncio
import json
from typing import Any

import boto3

from copytrading_app.core.config import Settings
from copytrading_app.domain.enums import QueueName
from copytrading_app.domain.types import ExecutionCommandPayload


class SqsTaskQueue:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = boto3.client("sqs", region_name=settings.aws_region)
        self._queue_urls: dict[str, str | None] = {
            QueueName.NORMAL_EXEC.value: settings.sqs_queue_url_normal,
            QueueName.RISK_PRIORITY.value: settings.sqs_queue_url_risk,
            QueueName.RECOVERY.value: settings.sqs_queue_url_recovery,
        }

    async def publish(self, payload: ExecutionCommandPayload) -> None:
        queue_url = self._queue_urls[payload.queue_name.value]
        if not queue_url:
            raise ValueError(f"missing queue URL for {payload.queue_name.value}")
        await asyncio.to_thread(
            self._client.send_message,
            QueueUrl=queue_url,
            MessageBody=payload.model_dump_json(),
            MessageGroupId=payload.message_group,
            MessageDeduplicationId=payload.idempotency_key,
        )

    async def consume(self, queue_name: str) -> ExecutionCommandPayload | None:
        queue_url = self._queue_urls.get(queue_name)
        if not queue_url:
            return None
        response = await asyncio.to_thread(
            self._client.receive_message,
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=1,
            VisibilityTimeout=self.settings.default_queue_visibility_seconds,
        )
        messages = response.get("Messages", [])
        if not messages:
            return None
        message = messages[0]
        body: dict[str, Any] = json.loads(message["Body"])
        await asyncio.to_thread(
            self._client.delete_message,
            QueueUrl=queue_url,
            ReceiptHandle=message["ReceiptHandle"],
        )
        return ExecutionCommandPayload.model_validate(body)


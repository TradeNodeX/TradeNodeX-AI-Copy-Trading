from __future__ import annotations

import asyncio
import base64
from typing import Protocol

import boto3

from copytrading_app.core.config import Settings


class SecretCipher(Protocol):
    async def encrypt(self, plaintext: str | None) -> str | None: ...

    async def decrypt(self, ciphertext: str | None) -> str | None: ...


class LocalSecretCipher:
    async def encrypt(self, plaintext: str | None) -> str | None:
        if plaintext is None:
            return None
        return "local:" + base64.b64encode(plaintext.encode("utf-8")).decode("utf-8")

    async def decrypt(self, ciphertext: str | None) -> str | None:
        if ciphertext is None:
            return None
        if ciphertext.startswith("local:"):
            raw = ciphertext.split("local:", 1)[1]
            return base64.b64decode(raw.encode("utf-8")).decode("utf-8")
        return ciphertext


class AwsKmsSecretCipher:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = boto3.client("kms", region_name=settings.aws_region)

    async def encrypt(self, plaintext: str | None) -> str | None:
        if plaintext is None:
            return None
        response = await asyncio.to_thread(
            self._client.encrypt,
            KeyId=self.settings.kms_key_id,
            Plaintext=plaintext.encode("utf-8"),
        )
        blob = response["CiphertextBlob"]
        return "aws-kms:" + base64.b64encode(blob).decode("utf-8")

    async def decrypt(self, ciphertext: str | None) -> str | None:
        if ciphertext is None:
            return None
        if not ciphertext.startswith("aws-kms:"):
            return ciphertext
        raw = base64.b64decode(ciphertext.split("aws-kms:", 1)[1].encode("utf-8"))
        response = await asyncio.to_thread(self._client.decrypt, CiphertextBlob=raw)
        return response["Plaintext"].decode("utf-8")


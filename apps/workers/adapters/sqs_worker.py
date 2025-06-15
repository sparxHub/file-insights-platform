import boto3, asyncio, logging, json, os
from typing import Any

log = logging.getLogger(__name__)

class SQSWorker:
    """
    Minimal SQS long-polling worker stub.
    Replace `handle_message` with real business logic later.
    """

    def __init__(self, queue_url: str | None = None):
        self.queue_url = queue_url or os.getenv("SQS_QUEUE_URL")
        self._client = boto3.client("sqs")

    async def run(self):
        log.info("SQS worker starting. Queue=%s", self.queue_url)
        while True:
            msgs = self._client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,  # long-poll
            ).get("Messages", [])
            for msg in msgs:
                await self.handle_message(json.loads(msg["Body"]))
                self._client.delete_message(
                    QueueUrl=self.queue_url,
                    ReceiptHandle=msg["ReceiptHandle"],
                )

    async def handle_message(self, payload: Any):
        log.info("Stub handler got message: %s", payload)
        # TODO: call app.services / db updates etc.

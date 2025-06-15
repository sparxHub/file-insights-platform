"""
Very light RabbitMQ consumer stub (uses pika).
Enable when you decide to switch away from SQS.
"""
import asyncio, logging, json, os, pika

log = logging.getLogger(__name__)

class RabbitWorker:
    def __init__(self, queue: str | None = None):
        self.queue = queue or os.getenv("RABBIT_QUEUE", "uploads")
        self._conn = pika.BlockingConnection(pika.URLParameters(os.getenv("RABBIT_URL", "amqp://guest:guest@localhost/")))
        self._chan = self._conn.channel()
        self._chan.queue_declare(queue=self.queue, durable=True)

    async def run(self):
        log.info("Rabbit worker starting. Queue=%s", self.queue)
        self._chan.basic_qos(prefetch_count=1)
        self._chan.basic_consume(queue=self.queue, on_message_callback=self._callback, auto_ack=False)
        self._chan.start_consuming()

    def _callback(self, ch, method, properties, body):
        payload = json.loads(body)
        log.info("Stub handler got message: %s", payload)
        # TODO business logic
        ch.basic_ack(delivery_tag=method.delivery_tag)

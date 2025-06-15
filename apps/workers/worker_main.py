import asyncio, os
from adapters.sqs_worker import SQSWorker

async def main():
    worker = SQSWorker()
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())

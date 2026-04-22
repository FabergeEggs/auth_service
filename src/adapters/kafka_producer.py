from aiokafka import AIOKafkaProducer
import json
from uuid import uuid4
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class KafkaEventProducer:
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self.producer: Optional[AIOKafkaProducer] = None

    async def start(self):
        if self.producer is not None:
            return
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode(),
        )
        await self.producer.start()
        logger.info(f"Kafka producer started, connected to {self.bootstrap_servers}")

    async def stop(self):
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

    async def send_event(self, event_type: str, data: Dict[str, Any]) -> None:
        if not self.producer:
            raise RuntimeError("Producer not started")

        event = {
            "event_id": str(uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

        # Validate payload before handing it off to the producer.
        json.dumps(event)

        await self.producer.send(event_type, event)
        logger.info(f"Event sent: {event_type}", extra={"event_id": event["event_id"]})

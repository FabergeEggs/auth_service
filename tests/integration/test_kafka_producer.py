import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
import json
from src.adapters.kafka_producer import KafkaEventProducer

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def kafka_producer():
    """Фикстура для Kafka продюсера"""
    producer = KafkaEventProducer(bootstrap_servers="localhost:9092")
    yield producer
    await producer.stop()


class TestKafkaProducerLifecycle:
    """Тесты жизненного цикла продюсера"""

    async def test_start_success(self, kafka_producer):
        """Тест успешного старта"""
        mock_producer = AsyncMock()

        with patch(
            "src.adapters.kafka_producer.AIOKafkaProducer", return_value=mock_producer
        ):
            await kafka_producer.start()

            assert kafka_producer.producer is not None
            mock_producer.start.assert_called_once()

    async def test_start_already_started(self, kafka_producer):
        """Тест повторного старта"""
        mock_producer = AsyncMock()
        kafka_producer.producer = mock_producer

        # Не должно быть ошибки
        await kafka_producer.start()

    async def test_stop_success(self, kafka_producer):
        """Тест успешной остановки"""
        mock_producer = AsyncMock()
        kafka_producer.producer = mock_producer

        await kafka_producer.stop()

        mock_producer.stop.assert_called_once()

    async def test_stop_not_started(self, kafka_producer):
        """Тест остановки не запущенного продюсера"""
        kafka_producer.producer = None

        # Не должно быть ошибки
        await kafka_producer.stop()


class TestKafkaProducerSendEvent:
    """Тесты отправки событий"""

    async def test_send_event_success(self, kafka_producer):
        """Тест успешной отправки события"""
        mock_producer = AsyncMock()
        kafka_producer.producer = mock_producer

        event_data = {
            "user_id": "user-123",
            "email": "test@example.com",
            "action": "register",
        }

        await kafka_producer.send_event("user.registered", event_data)

        mock_producer.send.assert_called_once()

        # Проверяем структуру отправленного события
        call_args = mock_producer.send.call_args
        topic = call_args[0][0]
        event = call_args[0][1]

        assert topic == "user.registered"
        assert event["event_type"] == "user.registered"
        assert event["data"] == event_data
        assert "event_id" in event
        assert "timestamp" in event

    async def test_send_event_not_started(self, kafka_producer):
        """Тест отправки события без запуска продюсера"""
        kafka_producer.producer = None

        with pytest.raises(RuntimeError, match="not started"):
            await kafka_producer.send_event("test.event", {"data": "test"})

    async def test_send_event_with_complex_data(self, kafka_producer):
        """Тест отправки сложных данных"""
        mock_producer = AsyncMock()
        kafka_producer.producer = mock_producer

        complex_data = {
            "user_id": "user-123",
            "metadata": {
                "ip": "192.168.1.1",
                "user_agent": "Mozilla/5.0",
                "timestamp": "2024-01-01T00:00:00Z",
            },
            "tags": ["important", "auth"],
            "nested": {"level1": {"level2": "value"}},
        }

        await kafka_producer.send_event("complex.event", complex_data)

        # Проверяем что данные сериализовались корректно
        call_args = mock_producer.send.call_args
        event = call_args[0][1]

        # Должны быть сериализуемы в JSON
        json.dumps(event)

    async def test_send_event_serialization_error(self, kafka_producer):
        """Тест ошибки сериализации"""
        mock_producer = AsyncMock()
        kafka_producer.producer = mock_producer

        # Данные с несериализуемым объектом
        bad_data = {
            "user_id": "user-123",
            "callback": lambda x: x,  # Функция не сериализуется
        }

        with pytest.raises(TypeError):
            await kafka_producer.send_event("bad.event", bad_data)

    async def test_send_event_kafka_error(self, kafka_producer):
        """Тест ошибки Kafka при отправке"""
        mock_producer = AsyncMock()
        mock_producer.send.side_effect = Exception("Kafka error")
        kafka_producer.producer = mock_producer

        with pytest.raises(Exception, match="Kafka error"):
            await kafka_producer.send_event("test.event", {"data": "test"})


class TestKafkaProducerEventFormat:
    """Тесты формата событий"""

    async def test_event_has_required_fields(self, kafka_producer):
        """Тест наличия обязательных полей в событии"""
        mock_producer = AsyncMock()
        kafka_producer.producer = mock_producer

        await kafka_producer.send_event("test.event", {"foo": "bar"})

        call_args = mock_producer.send.call_args
        event = call_args[0][1]

        assert "event_id" in event
        assert "event_type" in event
        assert "timestamp" in event
        assert "data" in event
        assert event["event_type"] == "test.event"
        assert event["data"] == {"foo": "bar"}

    async def test_event_id_is_unique(self, kafka_producer):
        """Тест уникальности event_id"""
        mock_producer = AsyncMock()
        kafka_producer.producer = mock_producer

        event_ids = set()

        for _ in range(10):
            await kafka_producer.send_event("test.event", {"iteration": _})
            call_args = mock_producer.send.call_args_list[-1]
            event = call_args[0][1]
            event_ids.add(event["event_id"])

        # Все ID должны быть уникальными
        assert len(event_ids) == 10

    async def test_timestamp_is_iso_format(self, kafka_producer):
        """Тест формата timestamp"""
        mock_producer = AsyncMock()
        kafka_producer.producer = mock_producer

        await kafka_producer.send_event("test.event", {})

        call_args = mock_producer.send.call_args
        event = call_args[0][1]

        # Проверяем что timestamp в ISO формате
        from datetime import datetime

        timestamp = event["timestamp"]
        datetime.fromisoformat(timestamp)  # Не должно быть исключения

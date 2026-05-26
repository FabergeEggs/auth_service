# auth_service

Регистрация, вход, refresh-токены через **Keycloak**. Публикует событие регистрации в Kafka.

## Порт и health

| Режим | URL |
|-------|-----|
| Docker (`mega-compose`) | http://localhost:8001 |
| Локально | http://localhost:8000 |

```bash
curl http://localhost:8001/health
```

## API (префикс `/auth`)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/auth/register` | Регистрация → Kafka `profile_service.user.registered` |
| POST | `/auth/login` | Логин, JWT |
| POST | `/auth/refresh` | Обновление токена |
| POST | `/auth/logout` | Выход |
| GET | `/health` | Keycloak доступен |

## Kafka

| Направление | Топик |
|-------------|--------|
| Out | `profile_service.user.registered` |

Константа: `src/kafka_topics.py` → `USER_REGISTERED`.

## Переменные окружения

| Переменная | Назначение |
|------------|------------|
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING` (по умолчанию `INFO`) |
| `KEYCLOAK_BASE_URL` | URL Keycloak |
| `KEYCLOAK_REALM` | Realm |
| `KEYCLOAK_CLIENT_ID` / `KEYCLOAK_CLIENT_SECRET` | Клиент |
| `REDPANDA_BOOTSTRAP_SERVERS` | Kafka |
| `KAFKA_ENABLED` | `true` / `false` |

## Логи

Формат: `время | уровень | logger | сообщение`.

**Docker:**

```bash
docker logs auth -f
docker logs keycloak -f
```

**Локально:** stdout процесса uvicorn.

Полезные logger-ы: `auth_service`, `auth_service.api`, `src.service.auth_service`, `src.adapters.kafka_producer`.

```bash
# только ошибки Kafka
docker logs auth 2>&1 | grep -i kafka
```

## Запуск

```bash
# из каталога сервиса
docker compose up -d --build

# стек целиком
cd ../infra_faberge && make auth-dev
```

## Тесты

```bash
# полный прогон: unit + API + Kafka mocks; Keycloak real — skip без флага
uv run pytest tests -q

# без любых integration (в т.ч. Kafka)
uv run pytest tests -m "not integration" -q

# реальный Keycloak (порт 8082 в mega-compose)
RUN_KEYCLOAK_INTEGRATION=1 KEYCLOAK_BASE_URL=http://localhost:8082 \
  uv run pytest tests/integration/test_keycloak_real.py -q
```

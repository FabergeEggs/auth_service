# Auth Service

В каталоге `auth_service`:

```bash
docker compose up -d --build
docker compose ps
```

Проверка health:

```bash
curl http://localhost:8000/health
```

Остановка:

```bash
docker compose down
```


После этого снова:

```bash
curl -X POST "http://localhost:8000/auth/register" -H "Content-Type: application/json" \
  -d "{\"email\":\"newuser@example.com\",\"password\":\"secret123\"}"
```



# Логи сервисов
docker logs auth-service -f
docker logs keycloak -f

# Перезапуск конкретного сервиса
docker-compose restart auth-service

# Полная пересборка
docker-compose down -v
docker-compose up -d --build

# Проверка пользователей в Keycloak
curl -s -X GET "http://localhost:8082/admin/realms/myrealm/users" \
  -H "Authorization: Bearer $MASTER_TOKEN" | jq '.'

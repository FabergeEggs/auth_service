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

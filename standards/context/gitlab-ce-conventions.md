# GitLab CE Conventions

## CI/CD Pipeline Structure

All microservices use GitLab CI/CD with a standardized pipeline structure:

- **stages:** `build`, `test`, `publish`, `deploy`
- **Default branch:** `main` (protected, no direct push)
- **Feature branches:** named `feature/<ticket>-<description>` or `fix/<ticket>-<description>`

## Container Image Conventions

- Images are built via **Kaniko** (no Docker daemon required — safe for shared runners)
- Registry: `registry.example.internal/<group>/<project>`
- Tags:
  - `latest` — последний успешный build на `main`
  - `<git-sha-short>` — неизменяемый тег по коммиту
  - `<semver>` — релизный тег при наличии git tag

## Merge Request Rules

- MR требует минимум 1 аппрувала от члена команды
- Ветка сливается через **squash merge** для чистоты истории
- Заголовок MR должен соответствовать Conventional Commits (`feat:`, `fix:`, `chore:` и т.д.)

## Environment Variables

Секреты хранятся в GitLab CI Variables (Settings → CI/CD → Variables):

| Переменная | Описание |
|-----------|----------|
| `REGISTRY_USER` | Логин для container registry |
| `REGISTRY_PASSWORD` | Пароль/токен для registry |
| `DEPLOY_TOKEN` | Токен для деплоя в K8s |

## Code Review Guidelines

- Reviewer должен проверить: корректность Dockerfile, переменные окружения, health checks
- Не мёржить без зелёного CI pipeline
- Комментарии в MR разрешать только автором или reviewer'ом

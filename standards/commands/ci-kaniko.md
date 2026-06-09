# /ci-kaniko — Сгенерировать GitLab CI job для сборки образа через Kaniko

Генерирует `.gitlab-ci.yml` фрагмент для сборки Docker-образа через Kaniko без Docker daemon.

## Использование

```
/ci-kaniko [опции]
```

## Параметры

- `--registry` — адрес container registry (например `registry.example.internal/mygroup/myservice`)
- `--dockerfile` — путь к Dockerfile (по умолчанию `Dockerfile`)
- `--context` — build context (по умолчанию `.`)

## Пример вывода

```yaml
build-image:
  stage: build
  image:
    name: gcr.io/kaniko-project/executor:v1.21.0-debug
    entrypoint: [""]
  script:
    - mkdir -p /kaniko/.docker
    - echo "{\"auths\":{\"${CI_REGISTRY}\":{\"auth\":\"$(echo -n ${CI_REGISTRY_USER}:${CI_REGISTRY_PASSWORD} | base64)\"}}}" > /kaniko/.docker/config.json
    - >
      /kaniko/executor
      --context "${CI_PROJECT_DIR}"
      --dockerfile "${CI_PROJECT_DIR}/Dockerfile"
      --destination "${CI_REGISTRY_IMAGE}:${CI_COMMIT_SHORT_SHA}"
      --destination "${CI_REGISTRY_IMAGE}:latest"
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
```

## Требования

- GitLab Runner с доступом к container registry
- Переменные `CI_REGISTRY_USER` и `CI_REGISTRY_PASSWORD` настроены в GitLab CI Variables
- Kaniko не требует privileged mode — безопасно на shared runners

## Полезные ссылки

- [Kaniko документация](https://github.com/GoogleContainerTools/kaniko)
- [GitLab Container Registry](https://docs.gitlab.com/ee/user/packages/container_registry/)

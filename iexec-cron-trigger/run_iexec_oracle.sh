#!/bin/bash

# Переходим в директорию, где лежат конфигурационные файлы iExec
cd /app/iexec-config

# Импортируем кошелек. PRIVATE_KEY и IEXEC_PASSWORD передаются как ENV переменные.
# --force перезапишет кошелек, если он уже импортирован, обеспечивая актуальность.
iexec wallet import "$PRIVATE_KEY" --password "$IEXEC_PASSWORD" --force

# Запускаем TEE-приложение в сети Arbitrum One Mainnet
# Параметры взяты из нашей предыдущей настройки GitLab CI/CD, чтобы обеспечить TEE-исполнение
iexec app run 0x62B576cE78Bbdf80fbd7b249A423cDBE21BB5FF6 \
  --callback 0xcfD218DfFced67D0197E9aE3739CC11eE61C2AD6 \
  --tag tee \
  --category 0 \
  --trust 1 \
  --chain arbitrum-mainnet \
  --password "$IEXEC_PASSWORD"

# Опционально: логируем время запуска для отладки
echo "iExec Oracle run initiated by Docker Cron at $(date)"

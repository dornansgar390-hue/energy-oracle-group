# Используем официальный образ Node.js, так как iExec CLI основан на Node.js
FROM node:20-slim

# Устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y \
    cron \
    git \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем iExec CLI глобально
RUN npm install -g iexec

# Создаем директорию для конфигурационных файлов iExec (chain.json, iexec.json и т.д.)
# Секреты (ключи) сюда НЕ копируются
WORKDIR /app/iexec-config

# Копируем конфигурационные файлы iExec. Их нужно будет поместить в папку рядом с Dockerfile
# ВАЖНО: убедитесь, что эти файлы (chain.json, iexec.json, deployed.json) находятся в той же папке,
# где вы будете запускать docker build, или в подпапке ./config
COPY ./chain.json ./
COPY ./iexec.json ./
COPY ./deployed.json ./

# Копируем скрипт, который будет запускать iExec команду
COPY run_iexec_oracle.sh /usr/local/bin/run_iexec_oracle.sh
RUN chmod +x /usr/local/bin/run_iexec_oracle.sh

# Настраиваем Cron: добавляем файл cronjob в системный cron
# Этот файл будет содержать расписание, например, "0 * * * * /usr/local/bin/run_iexec_oracle.sh >> /var/log/iexec_oracle.log 2>&1"
COPY cron_job /etc/cron.d/iexec-oracle-cron
RUN chmod 0644 /etc/cron.d/iexec-oracle-cron
RUN crontab /etc/cron.d/iexec-oracle-cron

# Запускаем cron-сервис
CMD ["cron", "-f"]

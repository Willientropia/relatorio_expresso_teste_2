# backend/Dockerfile
FROM python:3.11-slim

# Define o diretório de trabalho no container
WORKDIR /app

# Variáveis de ambiente para Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependências do sistema necessárias para o Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instala as dependências Python primeiro (incluindo chromedriver-autoinstaller)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copia o projeto
COPY . .

# Cria diretório para arquivos de mídia
RUN mkdir -p media/faturas media/temp_faturas

# Script para instalar ChromeDriver automaticamente ao iniciar
RUN echo '#!/bin/bash\n\
python -c "import chromedriver_autoinstaller; chromedriver_autoinstaller.install()"\n\
python manage.py migrate\n\
python manage.py runserver 0.0.0.0:8000' > /app/start.sh && \
chmod +x /app/start.sh

# Expõe a porta 8000
EXPOSE 8000

# Comando para rodar o script de inicialização
CMD ["/app/start.sh"]
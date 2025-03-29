FROM python:3.10-slim

# Installation des dépendances système
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-jdk \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Configuration de Java pour PySpark
ENV JAVA_HOME=/usr/lib/jvm/default-java

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir pyspark groq

# Copier le reste des fichiers de l'application
COPY . .

# Exposer le port 8004
EXPOSE 8004

# Commande pour démarrer l'application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
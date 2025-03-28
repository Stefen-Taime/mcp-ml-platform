FROM python:3.10-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Installer les bibliothèques pour Groq et Spark
RUN pip install --no-cache-dir groq pyspark

# Copier le reste des fichiers de l'application
COPY . .

# Exposer le port 8004
EXPOSE 8004

# Commande pour démarrer l'application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]

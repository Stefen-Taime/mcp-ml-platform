FROM bitnami/spark:latest

USER root

# Installation des dépendances Python
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Installation des packages Python nécessaires
RUN pip3 install --no-cache-dir \
    numpy \
    pandas \
    scikit-learn \
    pymongo \
    minio \
    pyspark

# Copie des fichiers de configuration
COPY spark-defaults.conf /opt/bitnami/spark/conf/

# Création du répertoire pour les applications Spark
RUN mkdir -p /opt/spark-apps
WORKDIR /opt/spark-apps

# Copie des applications Spark
COPY apps/ /opt/spark-apps/

# Définition des variables d'environnement
ENV SPARK_MASTER_URL=spark://spark-master:7077 \
    SPARK_WORKER_MEMORY=1G \
    SPARK_DRIVER_MEMORY=1G \
    SPARK_EXECUTOR_MEMORY=1G

# Exposition des ports
EXPOSE 8080 7077 6066

# Point d'entrée par défaut
CMD ["bash"]

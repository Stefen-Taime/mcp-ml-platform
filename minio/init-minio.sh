#!/bin/bash

# Script d'initialisation pour MinIO
# Ce script crée les buckets nécessaires pour la plateforme MCP ML

# Attendre que MinIO soit prêt
echo "Attente du démarrage de MinIO..."
until mc alias set myminio http://minio:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD} &>/dev/null
do
    echo "MinIO n'est pas encore prêt, nouvelle tentative dans 5 secondes..."
    sleep 5
done

echo "MinIO est prêt, création des buckets..."

# Créer les buckets
mc mb myminio/models --ignore-existing
mc mb myminio/datasets --ignore-existing
mc mb myminio/results --ignore-existing

# Configurer les politiques d'accès
mc policy set download myminio/models
mc policy set download myminio/datasets
mc policy set download myminio/results

echo "Configuration de MinIO terminée avec succès!"

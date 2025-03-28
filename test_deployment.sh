#!/bin/bash

# Script de test pour vérifier le déploiement complet de la plateforme MCP ML

echo "=== Test de déploiement de la plateforme MCP ML ==="
echo "Démarrage des services..."

# Démarrer les services
docker-compose up -d

# Attendre que les services soient prêts
echo "Attente du démarrage des services (30 secondes)..."
sleep 30

# Vérifier que tous les conteneurs sont en cours d'exécution
echo "=== Vérification des conteneurs ==="
CONTAINERS=$(docker-compose ps -q | wc -l)
RUNNING_CONTAINERS=$(docker-compose ps | grep "Up" | wc -l)

echo "Nombre total de conteneurs: $CONTAINERS"
echo "Conteneurs en cours d'exécution: $RUNNING_CONTAINERS"

if [ "$RUNNING_CONTAINERS" -eq "$CONTAINERS" ]; then
    echo "✅ Tous les conteneurs sont en cours d'exécution"
else
    echo "❌ Certains conteneurs ne sont pas en cours d'exécution"
    docker-compose ps
fi

# Vérifier l'accès à Nginx
echo "=== Vérification de l'accès à Nginx ==="
NGINX_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health)

if [ "$NGINX_STATUS" -eq 200 ]; then
    echo "✅ Nginx est accessible (code $NGINX_STATUS)"
else
    echo "❌ Nginx n'est pas accessible (code $NGINX_STATUS)"
fi

# Vérifier l'accès à l'API Gateway
echo "=== Vérification de l'accès à l'API Gateway ==="
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/health)

if [ "$API_STATUS" -eq 200 ]; then
    echo "✅ API Gateway est accessible (code $API_STATUS)"
else
    echo "❌ API Gateway n'est pas accessible (code $API_STATUS)"
fi

# Vérifier l'accès à MinIO
echo "=== Vérification de l'accès à MinIO ==="
MINIO_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/minio/)

if [ "$MINIO_STATUS" -eq 200 ]; then
    echo "✅ MinIO est accessible (code $MINIO_STATUS)"
else
    echo "❌ MinIO n'est pas accessible (code $MINIO_STATUS)"
fi

# Vérifier l'accès à Mongo Express
echo "=== Vérification de l'accès à Mongo Express ==="
MONGO_EXPRESS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/mongo-express/)

if [ "$MONGO_EXPRESS_STATUS" -eq 200 ]; then
    echo "✅ Mongo Express est accessible (code $MONGO_EXPRESS_STATUS)"
else
    echo "❌ Mongo Express n'est pas accessible (code $MONGO_EXPRESS_STATUS)"
fi

# Vérifier l'accès à Spark UI
echo "=== Vérification de l'accès à Spark UI ==="
SPARK_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/spark/)

if [ "$SPARK_STATUS" -eq 200 ]; then
    echo "✅ Spark UI est accessible (code $SPARK_STATUS)"
else
    echo "❌ Spark UI n'est pas accessible (code $SPARK_STATUS)"
fi

# Vérifier les logs pour détecter d'éventuelles erreurs
echo "=== Vérification des logs pour détecter des erreurs ==="
ERROR_COUNT=$(docker-compose logs | grep -i "error" | wc -l)
EXCEPTION_COUNT=$(docker-compose logs | grep -i "exception" | wc -l)

echo "Nombre d'erreurs détectées: $ERROR_COUNT"
echo "Nombre d'exceptions détectées: $EXCEPTION_COUNT"

if [ "$ERROR_COUNT" -eq 0 ] && [ "$EXCEPTION_COUNT" -eq 0 ]; then
    echo "✅ Aucune erreur ou exception détectée dans les logs"
else
    echo "⚠️ Des erreurs ou exceptions ont été détectées dans les logs"
fi

# Résumé des tests
echo "=== Résumé des tests ==="
if [ "$RUNNING_CONTAINERS" -eq "$CONTAINERS" ] && [ "$NGINX_STATUS" -eq 200 ] && [ "$API_STATUS" -eq 200 ]; then
    echo "✅ Le déploiement de base est fonctionnel"
    
    if [ "$MINIO_STATUS" -eq 200 ] && [ "$MONGO_EXPRESS_STATUS" -eq 200 ] && [ "$SPARK_STATUS" -eq 200 ]; then
        echo "✅ Tous les services sont accessibles"
        echo "✅ TEST GLOBAL: SUCCÈS"
    else
        echo "⚠️ Certains services ne sont pas accessibles"
        echo "⚠️ TEST GLOBAL: PARTIEL"
    fi
else
    echo "❌ Le déploiement de base n'est pas fonctionnel"
    echo "❌ TEST GLOBAL: ÉCHEC"
fi

echo "=== Fin des tests ==="

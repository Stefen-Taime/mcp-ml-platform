#!/bin/bash

# Créer un modèle
echo "Création d'un modèle..."
MODEL_RESPONSE=$(curl -s -X POST "http://localhost/api/models" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Modèle de test complet",
        "description": "Modèle pour tester Spark et Groq",
        "type": "regression",
        "framework": "scikit-learn",
        "version": "1.0"
    }')

MODEL_ID=$(echo $MODEL_RESPONSE | grep -o '"id":"[^"]*"' | cut -d':' -f2 | sed 's/"//g')
echo "Modèle créé avec ID: $MODEL_ID"

# Créer un déploiement
echo "Création d'un déploiement..."
DEPLOYMENT_RESPONSE=$(curl -s -X POST "http://localhost/api/deployments" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Déploiement de test complet",
        "description": "Déploiement pour tester Spark et Groq",
        "model_id": "'$MODEL_ID'",
        "environment": "production",
        "status": "active"
    }')

DEPLOYMENT_ID=$(echo $DEPLOYMENT_RESPONSE | grep -o '"id":"[^"]*"' | cut -d':' -f2 | sed 's/"//g')
echo "Déploiement créé avec ID: $DEPLOYMENT_ID"

# Test standard
echo "Exécution standard..."
EXECUTION_RESPONSE=$(curl -s -X POST "http://localhost/api/executions" \
    -H "Content-Type: application/json" \
    -d '{
        "deployment_id": "'$DEPLOYMENT_ID'",
        "parameters": {
            "input_data": {
                "experience": 5,
                "education": 16,
                "hours_per_week": 40,
                "age": 30
            }
        }
    }')

EXECUTION_ID=$(echo $EXECUTION_RESPONSE | grep -o '"id":"[^"]*"' | cut -d':' -f2 | sed 's/"//g')
echo "Exécution standard créée avec ID: $EXECUTION_ID"

# Attendre quelques secondes pour le traitement
echo "Attente du traitement..."
sleep 5

# Vérifier les résultats
echo "Vérification des résultats standard..."
curl -s "http://localhost/api/executions/$EXECUTION_ID/results"

# Test avec Spark
echo "Exécution avec Spark..."
SPARK_EXECUTION_RESPONSE=$(curl -s -X POST "http://localhost/api/executions" \
    -H "Content-Type: application/json" \
    -d '{
        "deployment_id": "'$DEPLOYMENT_ID'",
        "parameters": {
            "use_spark": true,
            "input_data": {
                "experience": 10,
                "education": 18,
                "hours_per_week": 45,
                "age": 35
            }
        }
    }')

SPARK_EXECUTION_ID=$(echo $SPARK_EXECUTION_RESPONSE | grep -o '"id":"[^"]*"' | cut -d':' -f2 | sed 's/"//g')
echo "Exécution Spark créée avec ID: $SPARK_EXECUTION_ID"

echo "Test terminé avec succès!"
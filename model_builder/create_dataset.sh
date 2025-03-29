#!/bin/bash
# Script pour créer un dataset de salaires via l'API

# URL de base de l'API
API_BASE_URL="http://localhost/api"

# Générer un ID unique pour le dataset
DATASET_ID=$(uuidgen || cat /proc/sys/kernel/random/uuid)
echo "ID du dataset généré: $DATASET_ID"

# Créer le dataset via l'API
echo "Création du dataset..."
RESPONSE=$(curl -s -X POST "$API_BASE_URL/datasets" \
    -H "Content-Type: application/json" \
    -d '{
        "id": "'$DATASET_ID'",
        "name": "Données de salaires",
        "description": "Dataset d'exemple pour la prédiction de salaires",
        "type": "tabular",
        "format": "csv",
        "version": "1.0",
        "has_file": true,
        "file_name": "salary_dataset.csv",
        "file_path": "'$DATASET_ID'/salary_dataset.csv",
        "columns": ["experience", "education", "hours_per_week", "age", "salary"],
        "row_count": 50
    }')

echo "Réponse: $RESPONSE"

echo ""
echo "============================================"
echo "Dataset de salaires créé avec succès!"
echo "ID du dataset: $DATASET_ID"
echo "Vous pouvez maintenant utiliser ce dataset dans votre application."
echo "============================================"
echo ""

# Tester le flux complet avec un modèle et un déploiement
echo "Souhaitez-vous tester le flux complet avec un modèle et un déploiement? (o/n)"
read REPONSE

if [ "$REPONSE" == "o" ] || [ "$REPONSE" == "O" ]; then
    echo "Création d'un modèle..."
    MODEL_RESPONSE=$(curl -s -X POST "$API_BASE_URL/models" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "Prédiction de salaire",
            "description": "Modèle de régression linéaire pour prédire les salaires",
            "type": "regression",
            "framework": "scikit-learn",
            "version": "1.0",
            "has_file": true,
            "file_path": "salary_prediction_model.pkl"
        }')
    
    MODEL_ID=$(echo $MODEL_RESPONSE | grep -o '"id":"[^"]*"' | cut -d':' -f2 | sed 's/"//g')
    
    if [ -z "$MODEL_ID" ]; then
        echo "Erreur: Impossible d'obtenir l'ID du modèle. Réponse: $MODEL_RESPONSE"
    else
        echo "Modèle créé avec l'ID: $MODEL_ID"
        
        echo "Création d'un déploiement..."
        DEPLOYMENT_RESPONSE=$(curl -s -X POST "$API_BASE_URL/deployments" \
            -H "Content-Type: application/json" \
            -d '{
                "name": "Déploiement avec dataset de salaires",
                "description": "Test avec dataset préchargé",
                "model_id": "'$MODEL_ID'",
                "environment": "production",
                "status": "active",
                "parameters": {
                    "dataset_id": "'$DATASET_ID'"
                }
            }')
        
        DEPLOYMENT_ID=$(echo $DEPLOYMENT_RESPONSE | grep -o '"id":"[^"]*"' | cut -d':' -f2 | sed 's/"//g')
        
        if [ -z "$DEPLOYMENT_ID" ]; then
            echo "Erreur: Impossible d'obtenir l'ID du déploiement. Réponse: $DEPLOYMENT_RESPONSE"
        else
            echo "Déploiement créé avec l'ID: $DEPLOYMENT_ID"
            
            echo "Création d'une exécution..."
            EXECUTION_RESPONSE=$(curl -s -X POST "$API_BASE_URL/executions" \
                -H "Content-Type: application/json" \
                -d '{
                    "deployment_id": "'$DEPLOYMENT_ID'",
                    "parameters": {
                        "dataset_id": "'$DATASET_ID'",
                        "filter_age": 30,
                        "min_hours": 35
                    }
                }')
            
            EXECUTION_ID=$(echo $EXECUTION_RESPONSE | grep -o '"id":"[^"]*"' | cut -d':' -f2 | sed 's/"//g')
            
            if [ -z "$EXECUTION_ID" ]; then
                echo "Erreur: Impossible d'obtenir l'ID de l'exécution. Réponse: $EXECUTION_RESPONSE"
            else
                echo "Exécution créée avec l'ID: $EXECUTION_ID"
                
                echo "Test de flux complet terminé avec succès!"
                echo "- Dataset: $DATASET_ID"
                echo "- Modèle: $MODEL_ID"
                echo "- Déploiement: $DEPLOYMENT_ID"
                echo "- Exécution: $EXECUTION_ID"
            fi
        fi
    fi
else
    echo "Test annulé."
fi

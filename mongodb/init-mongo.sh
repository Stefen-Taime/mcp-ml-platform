#!/bin/bash

# Script d'initialisation pour MongoDB
# Ce script crée les collections et les index nécessaires pour la plateforme MCP ML

# Attendre que MongoDB soit prêt
echo "Attente du démarrage de MongoDB..."
until mongosh --host mongodb --port 27017 -u ${MONGO_INITDB_ROOT_USERNAME} -p ${MONGO_INITDB_ROOT_PASSWORD} --authenticationDatabase admin --eval "db.adminCommand('ping')" &>/dev/null
do
    echo "MongoDB n'est pas encore prêt, nouvelle tentative dans 5 secondes..."
    sleep 5
done

echo "MongoDB est prêt, création des collections et des index..."

# Créer les collections et les index
mongosh --host mongodb --port 27017 -u ${MONGO_INITDB_ROOT_USERNAME} -p ${MONGO_INITDB_ROOT_PASSWORD} --authenticationDatabase admin <<EOF
use mcpml;

// Créer les collections
db.createCollection("models");
db.createCollection("datasets");
db.createCollection("deployments");
db.createCollection("executions");

// Créer les index
db.models.createIndex({ "id": 1 }, { unique: true });
db.datasets.createIndex({ "id": 1 }, { unique: true });
db.deployments.createIndex({ "id": 1 }, { unique: true });
db.deployments.createIndex({ "model_id": 1 });
db.executions.createIndex({ "id": 1 }, { unique: true });
db.executions.createIndex({ "deployment_id": 1 });
db.executions.createIndex({ "status": 1 });

// Insérer quelques données de démonstration
db.models.insertMany([
  {
    "id": "model-1",
    "name": "Modèle de classification d'images",
    "description": "Un modèle de classification d'images basé sur ResNet-50",
    "type": "classification",
    "framework": "PyTorch",
    "version": "1.0.0",
    "created_at": new Date(),
    "updated_at": new Date()
  },
  {
    "id": "model-2",
    "name": "Modèle de prédiction de ventes",
    "description": "Un modèle de prédiction des ventes basé sur XGBoost",
    "type": "regression",
    "framework": "scikit-learn",
    "version": "1.0.0",
    "created_at": new Date(),
    "updated_at": new Date()
  },
  {
    "id": "model-3",
    "name": "Modèle de génération de texte",
    "description": "Un modèle de génération de texte basé sur GPT",
    "type": "generation",
    "framework": "Hugging Face",
    "version": "1.0.0",
    "created_at": new Date(),
    "updated_at": new Date()
  }
]);

db.datasets.insertMany([
  {
    "id": "dataset-1",
    "name": "Dataset d'images CIFAR-10",
    "description": "Un dataset d'images pour la classification",
    "type": "image",
    "format": "PNG",
    "size": 162000000,
    "created_at": new Date(),
    "updated_at": new Date()
  },
  {
    "id": "dataset-2",
    "name": "Dataset de ventes",
    "description": "Un dataset de ventes historiques",
    "type": "tabular",
    "format": "CSV",
    "size": 25000000,
    "created_at": new Date(),
    "updated_at": new Date()
  }
]);

db.deployments.insertMany([
  {
    "id": "deployment-1",
    "name": "Déploiement du modèle de classification",
    "description": "Déploiement du modèle de classification d'images",
    "model_id": "model-1",
    "model_name": "Modèle de classification d'images",
    "environment": "production",
    "status": "active",
    "created_at": new Date(),
    "updated_at": new Date()
  },
  {
    "id": "deployment-2",
    "name": "Déploiement du modèle de prédiction",
    "description": "Déploiement du modèle de prédiction des ventes",
    "model_id": "model-2",
    "model_name": "Modèle de prédiction de ventes",
    "environment": "staging",
    "status": "active",
    "created_at": new Date(),
    "updated_at": new Date()
  }
]);

db.executions.insertMany([
  {
    "id": "execution-1",
    "deployment_id": "deployment-1",
    "deployment_name": "Déploiement du modèle de classification",
    "model_id": "model-1",
    "model_name": "Modèle de classification d'images",
    "status": "completed",
    "started_at": new Date(new Date().getTime() - 3600000),
    "completed_at": new Date(new Date().getTime() - 3540000),
    "duration": 60,
    "parameters": {
      "batch_size": 32,
      "learning_rate": 0.001
    },
    "metrics": {
      "accuracy": 0.92,
      "precision": 0.89,
      "recall": 0.94,
      "f1_score": 0.91
    },
    "updated_at": new Date()
  },
  {
    "id": "execution-2",
    "deployment_id": "deployment-2",
    "deployment_name": "Déploiement du modèle de prédiction",
    "model_id": "model-2",
    "model_name": "Modèle de prédiction de ventes",
    "status": "completed",
    "started_at": new Date(new Date().getTime() - 7200000),
    "completed_at": new Date(new Date().getTime() - 7140000),
    "duration": 60,
    "parameters": {
      "max_depth": 6,
      "n_estimators": 100
    },
    "metrics": {
      "rmse": 0.15,
      "mae": 0.12,
      "r2": 0.85
    },
    "updated_at": new Date()
  }
]);

print("Collections et index créés avec succès!");
print("Données de démonstration insérées avec succès!");
EOF

echo "Configuration de MongoDB terminée avec succès!"

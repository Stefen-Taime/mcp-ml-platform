#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour uploader un dataset de salaires directement dans MongoDB et MinIO
sans passer par l'API Gateway.
"""

import os
import base64
import uuid
import json
from datetime import datetime
from pymongo import MongoClient
from minio import Minio
import pandas as pd

# Configurations
MONGODB_URI = "mongodb://admin:adminpassword@mongodb:27017/mcpml?authSource=admin"
MINIO_ENDPOINT = "minio:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
MINIO_SECURE = False
DATASETS_BUCKET = "datasets"

# Nom du fichier CSV
CSV_FILENAME = "salary_dataset.csv"

def main():
    print(f"Chargement du fichier CSV: {CSV_FILENAME}")
    
    if not os.path.exists(CSV_FILENAME):
        print(f"Erreur: Le fichier {CSV_FILENAME} n'existe pas.")
        return
    
    # Lire le CSV avec pandas pour vérifier qu'il est valide
    try:
        df = pd.read_csv(CSV_FILENAME)
        print(f"CSV validé avec {len(df)} lignes et les colonnes: {', '.join(df.columns)}")
    except Exception as e:
        print(f"Erreur lors de la lecture du CSV: {e}")
        return
    
    # Connexion à MongoDB
    try:
        mongo_client = MongoClient(MONGODB_URI)
        db = mongo_client["mcpml"]
        datasets_collection = db["datasets"]
        print("Connexion à MongoDB établie")
    except Exception as e:
        print(f"Erreur de connexion à MongoDB: {e}")
        return
    
    # Connexion à MinIO
    try:
        minio_client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )
        
        # Créer le bucket s'il n'existe pas
        if not minio_client.bucket_exists(DATASETS_BUCKET):
            minio_client.make_bucket(DATASETS_BUCKET)
            print(f"Bucket '{DATASETS_BUCKET}' créé")
        else:
            print(f"Bucket '{DATASETS_BUCKET}' existe déjà")
    except Exception as e:
        print(f"Erreur de connexion à MinIO: {e}")
        return
    
    # Générer un ID unique pour le dataset
    dataset_id = str(uuid.uuid4())
    print(f"ID du dataset généré: {dataset_id}")
    
    # Uploader le fichier vers MinIO
    try:
        object_name = f"{dataset_id}/{CSV_FILENAME}"
        with open(CSV_FILENAME, 'rb') as file_data:
            file_size = os.path.getsize(CSV_FILENAME)
            minio_client.put_object(
                DATASETS_BUCKET,
                object_name,
                file_data,
                file_size,
                content_type="text/csv"
            )
        print(f"Fichier uploadé dans MinIO: {object_name}")
    except Exception as e:
        print(f"Erreur lors de l'upload vers MinIO: {e}")
        return
    
    # Créer l'entrée dans MongoDB
    try:
        dataset_data = {
            "id": dataset_id,
            "name": "Données de salaires",
            "description": "Dataset d'exemple pour la prédiction de salaires",
            "type": "tabular",
            "format": "csv",
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "has_file": True,
            "file_name": CSV_FILENAME,
            "file_path": object_name,
            "file_size": file_size,
            "content_type": "text/csv",
            "columns": list(df.columns),
            "row_count": len(df)
        }
        
        result = datasets_collection.insert_one(dataset_data)
        print(f"Document créé dans MongoDB avec _id: {result.inserted_id}")
    except Exception as e:
        print(f"Erreur lors de la création du document MongoDB: {e}")
        return
    
    print("\n============================================")
    print(f"Dataset de salaires uploadé avec succès!")
    print(f"ID du dataset: {dataset_id}")
    print("Vous pouvez maintenant utiliser ce dataset dans votre application.")
    print("============================================\n")
    
    # Afficher les commandes cURL pour utiliser le dataset
    print("Pour créer un déploiement avec ce dataset:")
    print(f'''
curl -X POST "http://localhost/api/deployments" \\
    -H "Content-Type: application/json" \\
    -d '{{
        "name": "Déploiement avec dataset de salaires",
        "description": "Test avec dataset préchargé",
        "model_id": "VOTRE_MODEL_ID",
        "environment": "production",
        "status": "active",
        "parameters": {{
            "dataset_id": "{dataset_id}"
        }}
    }}'
''')
    
    print("Pour créer une exécution avec ce dataset:")
    print(f'''
curl -X POST "http://localhost/api/executions" \\
    -H "Content-Type: application/json" \\
    -d '{{
        "deployment_id": "VOTRE_DEPLOYMENT_ID",
        "parameters": {{
            "dataset_id": "{dataset_id}",
            "filter_age": 30,
            "min_hours": 35
        }}
    }}'
''')

if __name__ == "__main__":
    main()
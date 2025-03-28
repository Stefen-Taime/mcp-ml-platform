from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import uuid
import json
from datetime import datetime
import os
from typing import Dict, Any, List, Optional
import pymongo
from pymongo import MongoClient
from minio import Minio
from minio.error import S3Error

app = FastAPI(title="Data MCP Server")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Pour le développement, à restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration MongoDB
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://admin:adminpassword@mongodb:27017/mcpml?authSource=admin")
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client["mcpml"]
datasets_collection = db["datasets"]

# Configuration MinIO
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)

# Bucket pour les datasets
DATASETS_BUCKET = "datasets"

# Vérifier si le bucket existe, sinon le créer
try:
    if not minio_client.bucket_exists(DATASETS_BUCKET):
        minio_client.make_bucket(DATASETS_BUCKET)
        print(f"Bucket '{DATASETS_BUCKET}' créé avec succès")
    else:
        print(f"Bucket '{DATASETS_BUCKET}' existe déjà")
except S3Error as e:
    print(f"Erreur lors de la vérification/création du bucket: {e}")

# Middleware pour logger les requêtes
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = datetime.now()
    
    # Log la requête entrante
    print(f"Request {request_id} started: {request.method} {request.url}")
    
    # Traiter la requête
    response = await call_next(request)
    
    # Calculer la durée
    duration = (datetime.now() - start_time).total_seconds()
    
    # Log la réponse
    print(f"Request {request_id} completed: {response.status_code} in {duration:.3f}s")
    
    return response

# Fonction pour créer une réponse MCP
def create_mcp_response(request_message: Dict[str, Any], payload: Dict[str, Any], status: str = "success") -> Dict[str, Any]:
    return {
        "mcp_version": "1.0",
        "message_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "sender": {
            "id": "data-mcp-server",
            "type": "data-mcp-server"
        },
        "recipient": request_message.get("sender", {"id": "unknown", "type": "unknown"}),
        "message_type": "response",
        "operation": request_message.get("operation", "unknown"),
        "status": status,
        "payload": payload,
        "metadata": {
            "request_id": request_message.get("message_id", "unknown")
        }
    }

# Fonction pour créer une réponse d'erreur MCP
def create_mcp_error_response(request_message: Dict[str, Any], error_message: str, status_code: int) -> Dict[str, Any]:
    return create_mcp_response(
        request_message,
        {"error": error_message, "status_code": status_code},
        "error"
    )

# Point d'entrée pour traiter les messages MCP
@app.post("/process")
async def process_mcp_message(message: Dict[str, Any]):
    try:
        operation = message.get("operation")
        
        # Router vers la fonction appropriée en fonction de l'opération
        if operation == "list_datasets":
            return await list_datasets(message)
        elif operation == "get_dataset":
            return await get_dataset(message)
        elif operation == "create_dataset":
            return await create_dataset(message)
        elif operation == "update_dataset":
            return await update_dataset(message)
        elif operation == "delete_dataset":
            return await delete_dataset(message)
        elif operation == "upload_data":
            return await upload_data(message)
        elif operation == "download_data":
            return await download_data(message)
        elif operation == "transform_data":
            return await transform_data(message)
        else:
            return create_mcp_error_response(message, f"Unsupported operation: {operation}", 400)
    
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        return create_mcp_error_response(message, f"Internal server error: {str(e)}", 500)

# Opérations sur les datasets
async def list_datasets(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Récupérer tous les datasets de la base de données
        datasets = list(datasets_collection.find({}, {"_id": 0}))
        
        return create_mcp_response(message, {"datasets": datasets})
    
    except Exception as e:
        print(f"Error listing datasets: {str(e)}")
        return create_mcp_error_response(message, f"Error listing datasets: {str(e)}", 500)

async def get_dataset(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        dataset_id = message.get("payload", {}).get("dataset_id")
        if not dataset_id:
            return create_mcp_error_response(message, "Dataset ID is required", 400)
        
        # Récupérer le dataset de la base de données
        dataset = datasets_collection.find_one({"id": dataset_id}, {"_id": 0})
        if not dataset:
            return create_mcp_error_response(message, f"Dataset with ID {dataset_id} not found", 404)
        
        return create_mcp_response(message, {"dataset": dataset})
    
    except Exception as e:
        print(f"Error getting dataset: {str(e)}")
        return create_mcp_error_response(message, f"Error getting dataset: {str(e)}", 500)

async def create_dataset(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        dataset_data = message.get("payload", {}).get("dataset", {})
        if not dataset_data:
            return create_mcp_error_response(message, "Dataset data is required", 400)
        
        # Générer un ID unique si non fourni
        if "id" not in dataset_data:
            dataset_data["id"] = str(uuid.uuid4())
        
        # Ajouter des timestamps
        dataset_data["created_at"] = datetime.now().isoformat()
        dataset_data["updated_at"] = dataset_data["created_at"]
        
        # Insérer le dataset dans la base de données
        datasets_collection.insert_one(dataset_data)
        
        return create_mcp_response(message, {"dataset": dataset_data})
    
    except pymongo.errors.DuplicateKeyError:
        return create_mcp_error_response(message, f"Dataset with ID {dataset_data.get('id')} already exists", 409)
    
    except Exception as e:
        print(f"Error creating dataset: {str(e)}")
        return create_mcp_error_response(message, f"Error creating dataset: {str(e)}", 500)

async def update_dataset(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        dataset_data = message.get("payload", {}).get("dataset", {})
        if not dataset_data or "id" not in dataset_data:
            return create_mcp_error_response(message, "Dataset data with ID is required", 400)
        
        dataset_id = dataset_data["id"]
        
        # Vérifier si le dataset existe
        existing_dataset = datasets_collection.find_one({"id": dataset_id})
        if not existing_dataset:
            return create_mcp_error_response(message, f"Dataset with ID {dataset_id} not found", 404)
        
        # Mettre à jour le timestamp
        dataset_data["updated_at"] = datetime.now().isoformat()
        if "created_at" not in dataset_data:
            dataset_data["created_at"] = existing_dataset.get("created_at")
        
        # Mettre à jour le dataset dans la base de données
        datasets_collection.update_one({"id": dataset_id}, {"$set": dataset_data})
        
        return create_mcp_response(message, {"dataset": dataset_data})
    
    except Exception as e:
        print(f"Error updating dataset: {str(e)}")
        return create_mcp_error_response(message, f"Error updating dataset: {str(e)}", 500)

async def delete_dataset(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        dataset_id = message.get("payload", {}).get("dataset_id")
        if not dataset_id:
            return create_mcp_error_response(message, "Dataset ID is required", 400)
        
        # Vérifier si le dataset existe
        existing_dataset = datasets_collection.find_one({"id": dataset_id})
        if not existing_dataset:
            return create_mcp_error_response(message, f"Dataset with ID {dataset_id} not found", 404)
        
        # Supprimer le dataset de la base de données
        datasets_collection.delete_one({"id": dataset_id})
        
        # Supprimer les fichiers associés dans MinIO
        try:
            objects = minio_client.list_objects(DATASETS_BUCKET, prefix=f"{dataset_id}/")
            for obj in objects:
                minio_client.remove_object(DATASETS_BUCKET, obj.object_name)
        except S3Error as e:
            print(f"Warning: Could not delete dataset files from MinIO: {str(e)}")
        
        return create_mcp_response(message, {"message": f"Dataset with ID {dataset_id} deleted successfully"})
    
    except Exception as e:
        print(f"Error deleting dataset: {str(e)}")
        return create_mcp_error_response(message, f"Error deleting dataset: {str(e)}", 500)

async def upload_data(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        payload = message.get("payload", {})
        dataset_id = payload.get("dataset_id")
        file_content = payload.get("file_content")
        file_name = payload.get("file_name")
        content_type = payload.get("content_type", "application/octet-stream")
        
        if not dataset_id or not file_content or not file_name:
            return create_mcp_error_response(message, "Dataset ID, file content, and file name are required", 400)
        
        # Vérifier si le dataset existe
        existing_dataset = datasets_collection.find_one({"id": dataset_id})
        if not existing_dataset:
            return create_mcp_error_response(message, f"Dataset with ID {dataset_id} not found", 404)
        
        # Chemin du fichier dans MinIO
        object_name = f"{dataset_id}/{file_name}"
        
        # Télécharger le fichier vers MinIO
        try:
            import base64
            import io
            
            # Décoder le contenu du fichier (supposé être en base64)
            decoded_content = base64.b64decode(file_content)
            file_data = io.BytesIO(decoded_content)
            file_size = len(decoded_content)
            
            minio_client.put_object(
                DATASETS_BUCKET,
                object_name,
                file_data,
                file_size,
                content_type=content_type
            )
            
            # Mettre à jour les métadonnées du dataset
            datasets_collection.update_one(
                {"id": dataset_id},
                {
                    "$set": {
                        "has_file": True,
                        "file_name": file_name,
                        "file_path": object_name,
                        "file_size": file_size,
                        "content_type": content_type,
                        "updated_at": datetime.now().isoformat()
                    }
                }
            )
            
            return create_mcp_response(message, {
                "message": f"File {file_name} uploaded successfully for dataset {dataset_id}",
                "file_path": object_name
            })
            
        except S3Error as e:
            return create_mcp_error_response(message, f"Error uploading file to MinIO: {str(e)}", 500)
    
    except Exception as e:
        print(f"Error uploading data: {str(e)}")
        return create_mcp_error_response(message, f"Error uploading data: {str(e)}", 500)

async def download_data(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        dataset_id = message.get("payload", {}).get("dataset_id")
        if not dataset_id:
            return create_mcp_error_response(message, "Dataset ID is required", 400)
        
        # Vérifier si le dataset existe
        existing_dataset = datasets_collection.find_one({"id": dataset_id})
        if not existing_dataset:
            return create_mcp_error_response(message, f"Dataset with ID {dataset_id} not found", 404)
        
        # Vérifier si le dataset a un fichier associé
        if not existing_dataset.get("has_file"):
            return create_mcp_error_response(message, f"Dataset with ID {dataset_id} has no associated file", 404)
        
        file_path = existing_dataset.get("file_path")
        
        # Récupérer le fichier depuis MinIO
        try:
            import base64
            import io
            
            response = minio_client.get_object(DATASETS_BUCKET, file_path)
            file_data = response.read()
            
            # Encoder le contenu du fichier en base64
            encoded_content = base64.b64encode(file_data).decode('utf-8')
            
            return create_mcp_response(message, {
                "dataset_id": dataset_id,
                "file_name": existing_dataset.get("file_name"),
                "content_type": existing_dataset.get("content_type"),
                "file_size": existing_dataset.get("file_size"),
                "file_content": encoded_content
            })
            
        except S3Error as e:
            return create_mcp_error_response(message, f"Error downloading file from MinIO: {str(e)}", 500)
    
    except Exception as e:
        print(f"Error downloading data: {str(e)}")
        return create_mcp_error_response(message, f"Error downloading data: {str(e)}", 500)

async def transform_data(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        payload = message.get("payload", {})
        dataset_id = payload.get("dataset_id")
        transformations = payload.get("transformations", [])
        
        if not dataset_id:
            return create_mcp_error_response(message, "Dataset ID is required", 400)
        
        # Vérifier si le dataset existe
        existing_dataset = datasets_collection.find_one({"id": dataset_id})
        if not existing_dataset:
            return create_mcp_error_response(message, f"Dataset with ID {dataset_id} not found", 404)
        
        # Vérifier si le dataset a un fichier associé
        if not existing_dataset.get("has_file"):
            return create_mcp_error_response(message, f"Dataset with ID {dataset_id} has no associated file", 404)
        
        # Dans un système réel, nous appliquerions ici les transformations aux données
        # Pour ce POC, nous simulons simplement une transformation réussie
        
        # Créer un nouveau dataset pour les données transformées
        transformed_dataset_id = str(uuid.uuid4())
        transformed_dataset = {
            "id": transformed_dataset_id,
            "name": f"Transformed {existing_dataset.get('name', 'Dataset')}",
            "description": f"Transformed version of dataset {dataset_id}",
            "source_dataset_id": dataset_id,
            "transformations": transformations,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "has_file": False  # Sera mis à jour après la création du fichier
        }
        
        # Insérer le nouveau dataset dans la base de données
        datasets_collection.insert_one(transformed_dataset)
        
        # Simuler une opération de transformation
        # Normalement, cela serait fait de manière asynchrone par un worker
        
        # Marquer le dataset comme transformé avec succès
        transformed_dataset["has_file"] = True
        transformed_dataset["file_name"] = f"transformed_{existing_dataset.get('file_name', 'data.csv')}"
        transformed_dataset["file_path"] = f"{transformed_dataset_id}/{transformed_dataset['file_name']}"
        transformed_dataset["file_size"] = existing_dataset.get("file_size", 0)  # Simulé
        transformed_dataset["content_type"] = existing_dataset.get("content_type", "text/csv")
        transformed_dataset["updated_at"] = datetime.now().isoformat()
        
        # Mettre à jour le dataset dans la base de données
        datasets_collection.update_one(
            {"id": transformed_dataset_id},
            {"$set": transformed_dataset}
        )
        
        return create_mcp_response(message, {
            "message": f"Data transformation completed for dataset {dataset_id}",
            "transformed_dataset_id": transformed_dataset_id,
            "transformed_dataset": transformed_dataset
        })
    
    except Exception as e:
        print(f"Error transforming data: {str(e)}")
        return create_mcp_error_response(message, f"Error transforming data: {str(e)}", 500)
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
from bson import ObjectId
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

# Classe d'encodeur JSON personnalisé pour MongoDB
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Fonction pour convertir les ObjectId en chaînes de caractères
def mongo_to_json_serializable(obj):
    if isinstance(obj, dict):
        return {k: mongo_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [mongo_to_json_serializable(item) for item in obj]
    elif isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj

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
    # Convertir le payload pour qu'il soit sérialisable en JSON
    serializable_payload = mongo_to_json_serializable(payload)
    
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
        "payload": serializable_payload,
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
        print(f"Received MCP request for operation: {operation}")
        print(f"Request payload: {json.dumps(message.get('payload', {}), cls=MongoJSONEncoder)}")
        
        # Router vers la fonction appropriée en fonction de l'opération
        if operation == "list_datasets":
            response = await list_datasets(message)
        elif operation == "get_dataset":
            response = await get_dataset(message)
        elif operation == "create_dataset":
            response = await create_dataset(message)
        elif operation == "update_dataset":
            response = await update_dataset(message)
        elif operation == "delete_dataset":
            response = await delete_dataset(message)
        elif operation == "upload_data":
            response = await upload_data(message)
        elif operation == "download_data":
            response = await download_data(message)
        elif operation == "transform_data":
            response = await transform_data(message)
        else:
            response = create_mcp_error_response(message, f"Unsupported operation: {operation}", 400)
        
        print(f"Sending MCP response for operation: {operation}")
        return response
    
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        return create_mcp_error_response(message, f"Internal server error: {str(e)}", 500)

# Opérations sur les datasets
async def list_datasets(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Récupérer tous les datasets de la base de données
        datasets = list(datasets_collection.find({}))
        
        # Convertir les datasets en objets sérialisables en JSON
        serializable_datasets = mongo_to_json_serializable(datasets)
        
        return create_mcp_response(message, {"datasets": serializable_datasets})
    
    except Exception as e:
        print(f"Error listing datasets: {str(e)}")
        return create_mcp_error_response(message, f"Error listing datasets: {str(e)}", 500)

async def get_dataset(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        dataset_id = message.get("payload", {}).get("dataset_id")
        if not dataset_id:
            return create_mcp_error_response(message, "Dataset ID is required", 400)
        
        # Récupérer le dataset de la base de données
        dataset = datasets_collection.find_one({"id": dataset_id})
        if not dataset:
            return create_mcp_error_response(message, f"Dataset with ID {dataset_id} not found", 404)
        
        # Convertir le dataset en objet sérialisable en JSON
        serializable_dataset = mongo_to_json_serializable(dataset)
        
        return create_mcp_response(message, {"dataset": serializable_dataset})
    
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
        
        # Log la création du dataset
        print(f"Creating dataset with ID: {dataset_data['id']}")
        
        # Insérer le dataset dans la base de données
        datasets_collection.insert_one(dataset_data)
        
        # Convertir le dataset en objet sérialisable en JSON
        serializable_dataset = mongo_to_json_serializable(dataset_data)
        
        return create_mcp_response(message, {"dataset": serializable_dataset})
    
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
        
        # Convertir l'objet existant pour accès compatible
        existing_dataset = mongo_to_json_serializable(existing_dataset)
        
        # Mettre à jour le timestamp
        dataset_data["updated_at"] = datetime.now().isoformat()
        if "created_at" not in dataset_data:
            dataset_data["created_at"] = existing_dataset.get("created_at")
        
        # Mettre à jour le dataset dans la base de données
        datasets_collection.update_one({"id": dataset_id}, {"$set": dataset_data})
        
        # Log la mise à jour
        print(f"Dataset updated with ID: {dataset_id}")
        
        # Convertir le dataset en objet sérialisable en JSON
        serializable_dataset = mongo_to_json_serializable(dataset_data)
        
        return create_mcp_response(message, {"dataset": serializable_dataset})
    
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
        
        # Log la suppression
        print(f"Dataset deleted with ID: {dataset_id}")
        
        # Supprimer les fichiers associés dans MinIO
        try:
            objects = minio_client.list_objects(DATASETS_BUCKET, prefix=f"{dataset_id}/")
            for obj in objects:
                minio_client.remove_object(DATASETS_BUCKET, obj.object_name)
                print(f"Deleted object from MinIO: {obj.object_name}")
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
        
        # Convertir l'objet existant pour accès compatible
        existing_dataset = mongo_to_json_serializable(existing_dataset)
        
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
            
            # Log l'upload
            print(f"File uploaded to MinIO: {object_name}, size: {file_size}")
            
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
            print(f"Error uploading file to MinIO: {str(e)}")
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
        
        # Convertir l'objet existant pour accès compatible
        existing_dataset = mongo_to_json_serializable(existing_dataset)
        
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
            
            # Log le téléchargement
            print(f"File downloaded from MinIO: {file_path}, size: {len(file_data)}")
            
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
            print(f"Error downloading file from MinIO: {str(e)}")
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
        
        # Convertir l'objet existant pour accès compatible
        existing_dataset = mongo_to_json_serializable(existing_dataset)
        
        # Vérifier si le dataset a un fichier associé
        if not existing_dataset.get("has_file"):
            return create_mcp_error_response(message, f"Dataset with ID {dataset_id} has no associated file", 404)
        
        # Log la transformation
        print(f"Transforming dataset with ID: {dataset_id}")
        
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
        
        # Convertir le dataset transformé en objet sérialisable en JSON
        serializable_transformed_dataset = mongo_to_json_serializable(transformed_dataset)
        
        return create_mcp_response(message, {
            "message": f"Data transformation completed for dataset {dataset_id}",
            "transformed_dataset_id": transformed_dataset_id,
            "transformed_dataset": serializable_transformed_dataset
        })
    
    except Exception as e:
        print(f"Error transforming data: {str(e)}")
        return create_mcp_error_response(message, f"Error transforming data: {str(e)}", 500)

# Route de santé
@app.get("/health")
async def health_check():
    try:
        # Vérifier la connexion à MongoDB
        mongo_status = "ok" if mongo_client.server_info() else "error"
        
        # Vérifier la connexion à MinIO
        minio_status = "ok" if minio_client.bucket_exists(DATASETS_BUCKET) else "error"
        
        status = "ok" if mongo_status == "ok" and minio_status == "ok" else "error"
        
        return {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "services": {
                "mongodb": mongo_status,
                "minio": minio_status
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
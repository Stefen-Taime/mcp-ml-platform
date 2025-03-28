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

app = FastAPI(title="Model MCP Server")

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
models_collection = db["models"]

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

# Bucket pour les modèles
MODELS_BUCKET = "models"

# Vérifier si le bucket existe, sinon le créer
try:
    if not minio_client.bucket_exists(MODELS_BUCKET):
        minio_client.make_bucket(MODELS_BUCKET)
        print(f"Bucket '{MODELS_BUCKET}' créé avec succès")
    else:
        print(f"Bucket '{MODELS_BUCKET}' existe déjà")
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
            "id": "model-mcp-server",
            "type": "model-mcp-server"
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
        if operation == "list_models":
            return await list_models(message)
        elif operation == "get_model":
            return await get_model(message)
        elif operation == "create_model":
            return await create_model(message)
        elif operation == "update_model":
            return await update_model(message)
        elif operation == "delete_model":
            return await delete_model(message)
        elif operation == "upload_model_file":
            return await upload_model_file(message)
        elif operation == "download_model_file":
            return await download_model_file(message)
        else:
            return create_mcp_error_response(message, f"Unsupported operation: {operation}", 400)
    
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        return create_mcp_error_response(message, f"Internal server error: {str(e)}", 500)

# Opérations sur les modèles
async def list_models(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Récupérer tous les modèles de la base de données
        models = list(models_collection.find({}, {"_id": 0}))
        
        return create_mcp_response(message, {"models": models})
    
    except Exception as e:
        print(f"Error listing models: {str(e)}")
        return create_mcp_error_response(message, f"Error listing models: {str(e)}", 500)

async def get_model(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        model_id = message.get("payload", {}).get("model_id")
        if not model_id:
            return create_mcp_error_response(message, "Model ID is required", 400)
        
        # Récupérer le modèle de la base de données
        model = models_collection.find_one({"id": model_id}, {"_id": 0})
        if not model:
            return create_mcp_error_response(message, f"Model with ID {model_id} not found", 404)
        
        return create_mcp_response(message, {"model": model})
    
    except Exception as e:
        print(f"Error getting model: {str(e)}")
        return create_mcp_error_response(message, f"Error getting model: {str(e)}", 500)

async def create_model(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        model_data = message.get("payload", {}).get("model", {})
        if not model_data:
            return create_mcp_error_response(message, "Model data is required", 400)
        
        # Générer un ID unique si non fourni
        if "id" not in model_data:
            model_data["id"] = str(uuid.uuid4())
        
        # Ajouter des timestamps
        model_data["created_at"] = datetime.now().isoformat()
        model_data["updated_at"] = model_data["created_at"]
        
        # Insérer le modèle dans la base de données
        models_collection.insert_one(model_data)
        
        return create_mcp_response(message, {"model": model_data})
    
    except pymongo.errors.DuplicateKeyError:
        return create_mcp_error_response(message, f"Model with ID {model_data.get('id')} already exists", 409)
    
    except Exception as e:
        print(f"Error creating model: {str(e)}")
        return create_mcp_error_response(message, f"Error creating model: {str(e)}", 500)

async def update_model(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        model_data = message.get("payload", {}).get("model", {})
        if not model_data or "id" not in model_data:
            return create_mcp_error_response(message, "Model data with ID is required", 400)
        
        model_id = model_data["id"]
        
        # Vérifier si le modèle existe
        existing_model = models_collection.find_one({"id": model_id})
        if not existing_model:
            return create_mcp_error_response(message, f"Model with ID {model_id} not found", 404)
        
        # Mettre à jour le timestamp
        model_data["updated_at"] = datetime.now().isoformat()
        if "created_at" not in model_data:
            model_data["created_at"] = existing_model.get("created_at")
        
        # Mettre à jour le modèle dans la base de données
        models_collection.update_one({"id": model_id}, {"$set": model_data})
        
        return create_mcp_response(message, {"model": model_data})
    
    except Exception as e:
        print(f"Error updating model: {str(e)}")
        return create_mcp_error_response(message, f"Error updating model: {str(e)}", 500)

async def delete_model(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        model_id = message.get("payload", {}).get("model_id")
        if not model_id:
            return create_mcp_error_response(message, "Model ID is required", 400)
        
        # Vérifier si le modèle existe
        existing_model = models_collection.find_one({"id": model_id})
        if not existing_model:
            return create_mcp_error_response(message, f"Model with ID {model_id} not found", 404)
        
        # Supprimer le modèle de la base de données
        models_collection.delete_one({"id": model_id})
        
        # Supprimer les fichiers associés dans MinIO
        try:
            objects = minio_client.list_objects(MODELS_BUCKET, prefix=f"{model_id}/")
            for obj in objects:
                minio_client.remove_object(MODELS_BUCKET, obj.object_name)
        except S3Error as e:
            print(f"Warning: Could not delete model files from MinIO: {str(e)}")
        
        return create_mcp_response(message, {"message": f"Model with ID {model_id} deleted successfully"})
    
    except Exception as e:
        print(f"Error deleting model: {str(e)}")
        return create_mcp_error_response(message, f"Error deleting model: {str(e)}", 500)

async def upload_model_file(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        payload = message.get("payload", {})
        model_id = payload.get("model_id")
        file_content = payload.get("file_content")
        file_name = payload.get("file_name")
        content_type = payload.get("content_type", "application/octet-stream")
        
        if not model_id or not file_content or not file_name:
            return create_mcp_error_response(message, "Model ID, file content, and file name are required", 400)
        
        # Vérifier si le modèle existe
        existing_model = models_collection.find_one({"id": model_id})
        if not existing_model:
            return create_mcp_error_response(message, f"Model with ID {model_id} not found", 404)
        
        # Chemin du fichier dans MinIO
        object_name = f"{model_id}/{file_name}"
        
        # Télécharger le fichier vers MinIO
        try:
            import base64
            import io
            
            # Décoder le contenu du fichier (supposé être en base64)
            decoded_content = base64.b64decode(file_content)
            file_data = io.BytesIO(decoded_content)
            file_size = len(decoded_content)
            
            minio_client.put_object(
                MODELS_BUCKET,
                object_name,
                file_data,
                file_size,
                content_type=content_type
            )
            
            # Mettre à jour les métadonnées du modèle
            models_collection.update_one(
                {"id": model_id},
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
                "message": f"File {file_name} uploaded successfully for model {model_id}",
                "file_path": object_name
            })
            
        except S3Error as e:
            return create_mcp_error_response(message, f"Error uploading file to MinIO: {str(e)}", 500)
    
    except Exception as e:
        print(f"Error uploading model file: {str(e)}")
        return create_mcp_error_response(message, f"Error uploading model file: {str(e)}", 500)

async def download_model_file(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        model_id = message.get("payload", {}).get("model_id")
        if not model_id:
            return create_mcp_error_response(message, "Model ID is required", 400)
        
        # Vérifier si le modèle existe
        existing_model = models_collection.find_one({"id": model_id})
        if not existing_model:
            return create_mcp_error_response(message, f"Model with ID {model_id} not found", 404)
        
        # Vérifier si le modèle a un fichier associé
        if not existing_model.get("has_file"):
            return create_mcp_error_response(message, f"Model with ID {model_id} has no associated file", 404)
        
        file_path = existing_model.get("file_path")
        
        # Récupérer le fichier depuis MinIO
        try:
            import base64
            import io
            
            response = minio_client.get_object(MODELS_BUCKET, file_path)
            file_data = response.read()
            
            # Encoder le contenu du fichier en base64
            encoded_content = base64.b64encode(file_data).decode('utf-8')
            
            return create_mcp_response(message, {
                "model_id": model_id,
                "file_name": existing_model.get("file_name"),
                "content_type": existing_model.get("content_type"),
                "file_size": existing_model.get("file_size"),
                "file_content": encoded_content
            })
            
        except S3Error as e:
            return create_mcp_error_response(message, f"Error downloading file from MinIO: {str(e)}", 500)
    
    except Exception as e:
        print(f"Error downloading model file: {str(e)}")
        return create_mcp_error_response(message, f"Error downloading model file: {str(e)}", 500)

# Route de santé
@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

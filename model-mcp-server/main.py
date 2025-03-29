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
    # Convertir tous les éléments du payload pour qu'ils soient sérialisables en JSON
    serializable_payload = mongo_to_json_serializable(payload)
    
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
        if operation == "list_models":
            response = await list_models(message)
        elif operation == "get_model":
            response = await get_model(message)
        elif operation == "create_model":
            response = await create_model(message)
        elif operation == "update_model":
            response = await update_model(message)
        elif operation == "delete_model":
            response = await delete_model(message)
        elif operation == "upload_model_file":
            response = await upload_model_file(message)
        elif operation == "download_model_file":
            response = await download_model_file(message)
        else:
            response = create_mcp_error_response(message, f"Unsupported operation: {operation}", 400)
        
        print(f"Sending MCP response for operation: {operation}")
        return response
    
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        return create_mcp_error_response(message, f"Internal server error: {str(e)}", 500)

# Opérations sur les modèles
async def list_models(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Récupérer tous les modèles de la base de données
        models = list(models_collection.find({}))
        
        # Convertir les modèles en objets sérialisables en JSON
        serializable_models = mongo_to_json_serializable(models)
        
        return create_mcp_response(message, {"models": serializable_models})
    
    except Exception as e:
        print(f"Error listing models: {str(e)}")
        return create_mcp_error_response(message, f"Error listing models: {str(e)}", 500)

async def get_model(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        model_id = message.get("payload", {}).get("model_id")
        if not model_id:
            return create_mcp_error_response(message, "Model ID is required", 400)
        
        # Récupérer le modèle de la base de données
        model = models_collection.find_one({"id": model_id})
        if not model:
            return create_mcp_error_response(message, f"Model with ID {model_id} not found", 404)
        
        # Convertir le modèle en objet sérialisable en JSON
        serializable_model = mongo_to_json_serializable(model)
        
        return create_mcp_response(message, {"model": serializable_model})
    
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
        
        # Log la création du modèle
        print(f"Model created with ID: {model_data['id']}")
        
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
        
        # Convertir l'objet existant pour accès compatible
        existing_model = mongo_to_json_serializable(existing_model)
        
        # Mettre à jour le timestamp
        model_data["updated_at"] = datetime.now().isoformat()
        if "created_at" not in model_data:
            model_data["created_at"] = existing_model.get("created_at")
        
        # Mettre à jour le modèle dans la base de données
        models_collection.update_one({"id": model_id}, {"$set": model_data})
        
        # Log la mise à jour
        print(f"Model updated with ID: {model_id}")
        
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
        
        # Log la suppression
        print(f"Model deleted with ID: {model_id}")
        
        # Supprimer les fichiers associés dans MinIO
        try:
            objects = minio_client.list_objects(MODELS_BUCKET, prefix=f"{model_id}/")
            for obj in objects:
                minio_client.remove_object(MODELS_BUCKET, obj.object_name)
                print(f"Deleted object from MinIO: {obj.object_name}")
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
            
            # Log l'upload
            print(f"File uploaded to MinIO: {object_name}, size: {file_size}")
            
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
            print(f"Error uploading file to MinIO: {str(e)}")
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
        
        # Convertir l'objet existant pour accès compatible
        existing_model = mongo_to_json_serializable(existing_model)
        
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
            
            # Log le téléchargement
            print(f"File downloaded from MinIO: {file_path}, size: {len(file_data)}")
            
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
            print(f"Error downloading file from MinIO: {str(e)}")
            return create_mcp_error_response(message, f"Error downloading file from MinIO: {str(e)}", 500)
    
    except Exception as e:
        print(f"Error downloading model file: {str(e)}")
        return create_mcp_error_response(message, f"Error downloading model file: {str(e)}", 500)

# Route de santé
@app.get("/health")
async def health_check():
    try:
        # Vérifier la connexion à MongoDB
        mongo_status = "ok" if mongo_client.server_info() else "error"
        
        # Vérifier la connexion à MinIO
        minio_status = "ok" if minio_client.bucket_exists(MODELS_BUCKET) else "error"
        
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
    uvicorn.run(app, host="0.0.0.0", port=8002)
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
import groq

app = FastAPI(title="Execution MCP Server")

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
deployments_collection = db["deployments"]
executions_collection = db["executions"]

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

# Configuration Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
groq_client = groq.Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Configuration Spark
SPARK_MASTER_URL = os.getenv("SPARK_MASTER_URL", "spark://spark-master:7077")

# Buckets pour les résultats d'exécution
RESULTS_BUCKET = "results"

# Vérifier si le bucket existe, sinon le créer
try:
    if not minio_client.bucket_exists(RESULTS_BUCKET):
        minio_client.make_bucket(RESULTS_BUCKET)
        print(f"Bucket '{RESULTS_BUCKET}' créé avec succès")
    else:
        print(f"Bucket '{RESULTS_BUCKET}' existe déjà")
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
            "id": "execution-mcp-server",
            "type": "execution-mcp-server"
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
        if operation == "list_deployments":
            return await list_deployments(message)
        elif operation == "get_deployment":
            return await get_deployment(message)
        elif operation == "create_deployment":
            return await create_deployment(message)
        elif operation == "update_deployment":
            return await update_deployment(message)
        elif operation == "delete_deployment":
            return await delete_deployment(message)
        elif operation == "list_executions":
            return await list_executions(message)
        elif operation == "get_execution":
            return await get_execution(message)
        elif operation == "create_execution":
            return await create_execution(message)
        elif operation == "cancel_execution":
            return await cancel_execution(message)
        elif operation == "get_execution_results":
            return await get_execution_results(message)
        else:
            return create_mcp_error_response(message, f"Unsupported operation: {operation}", 400)
    
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        return create_mcp_error_response(message, f"Internal server error: {str(e)}", 500)

# Opérations sur les déploiements
async def list_deployments(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Récupérer tous les déploiements de la base de données
        deployments = list(deployments_collection.find({}, {"_id": 0}))
        
        return create_mcp_response(message, {"deployments": deployments})
    
    except Exception as e:
        print(f"Error listing deployments: {str(e)}")
        return create_mcp_error_response(message, f"Error listing deployments: {str(e)}", 500)

async def get_deployment(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        deployment_id = message.get("payload", {}).get("deployment_id")
        if not deployment_id:
            return create_mcp_error_response(message, "Deployment ID is required", 400)
        
        # Récupérer le déploiement de la base de données
        deployment = deployments_collection.find_one({"id": deployment_id}, {"_id": 0})
        if not deployment:
            return create_mcp_error_response(message, f"Deployment with ID {deployment_id} not found", 404)
        
        return create_mcp_response(message, {"deployment": deployment})
    
    except Exception as e:
        print(f"Error getting deployment: {str(e)}")
        return create_mcp_error_response(message, f"Error getting deployment: {str(e)}", 500)

async def create_deployment(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        deployment_data = message.get("payload", {}).get("deployment", {})
        if not deployment_data:
            return create_mcp_error_response(message, "Deployment data is required", 400)
        
        # Vérifier que le modèle est spécifié
        if "model_id" not in deployment_data:
            return create_mcp_error_response(message, "Model ID is required for deployment", 400)
        
        # Générer un ID unique si non fourni
        if "id" not in deployment_data:
            deployment_data["id"] = str(uuid.uuid4())
        
        # Ajouter des timestamps et statut par défaut
        deployment_data["created_at"] = datetime.now().isoformat()
        deployment_data["updated_at"] = deployment_data["created_at"]
        deployment_data["status"] = deployment_data.get("status", "inactive")
        
        # Insérer le déploiement dans la base de données
        deployments_collection.insert_one(deployment_data)
        
        return create_mcp_response(message, {"deployment": deployment_data})
    
    except pymongo.errors.DuplicateKeyError:
        return create_mcp_error_response(message, f"Deployment with ID {deployment_data.get('id')} already exists", 409)
    
    except Exception as e:
        print(f"Error creating deployment: {str(e)}")
        return create_mcp_error_response(message, f"Error creating deployment: {str(e)}", 500)

async def update_deployment(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        deployment_data = message.get("payload", {}).get("deployment", {})
        if not deployment_data or "id" not in deployment_data:
            return create_mcp_error_response(message, "Deployment data with ID is required", 400)
        
        deployment_id = deployment_data["id"]
        
        # Vérifier si le déploiement existe
        existing_deployment = deployments_collection.find_one({"id": deployment_id})
        if not existing_deployment:
            return create_mcp_error_response(message, f"Deployment with ID {deployment_id} not found", 404)
        
        # Mettre à jour le timestamp
        deployment_data["updated_at"] = datetime.now().isoformat()
        if "created_at" not in deployment_data:
            deployment_data["created_at"] = existing_deployment.get("created_at")
        
        # Mettre à jour le déploiement dans la base de données
        deployments_collection.update_one({"id": deployment_id}, {"$set": deployment_data})
        
        return create_mcp_response(message, {"deployment": deployment_data})
    
    except Exception as e:
        print(f"Error updating deployment: {str(e)}")
        return create_mcp_error_response(message, f"Error updating deployment: {str(e)}", 500)

async def delete_deployment(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        deployment_id = message.get("payload", {}).get("deployment_id")
        if not deployment_id:
            return create_mcp_error_response(message, "Deployment ID is required", 400)
        
        # Vérifier si le déploiement existe
        existing_deployment = deployments_collection.find_one({"id": deployment_id})
        if not existing_deployment:
            return create_mcp_error_response(message, f"Deployment with ID {deployment_id} not found", 404)
        
        # Vérifier s'il y a des exécutions en cours pour ce déploiement
        active_executions = executions_collection.find_one({
            "deployment_id": deployment_id,
            "status": {"$in": ["pending", "running"]}
        })
        if active_executions:
            return create_mcp_error_response(
                message, 
                f"Cannot delete deployment with active executions. Cancel executions first.", 
                409
            )
        
        # Supprimer le déploiement de la base de données
        deployments_collection.delete_one({"id": deployment_id})
        
        return create_mcp_response(message, {"message": f"Deployment with ID {deployment_id} deleted successfully"})
    
    except Exception as e:
        print(f"Error deleting deployment: {str(e)}")
        return create_mcp_error_response(message, f"Error deleting deployment: {str(e)}", 500)

# Opérations sur les exécutions
async def list_executions(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Filtres optionnels
        payload = message.get("payload", {})
        deployment_id = payload.get("deployment_id")
        status = payload.get("status")
        
        # Construire le filtre
        filter_query = {}
        if deployment_id:
            filter_query["deployment_id"] = deployment_id
        if status:
            filter_query["status"] = status
        
        # Récupérer les exécutions de la base de données
        executions = list(executions_collection.find(filter_query, {"_id": 0}))
        
        return create_mcp_response(message, {"executions": executions})
    
    except Exception as e:
        print(f"Error listing executions: {str(e)}")
        return create_mcp_error_response(message, f"Error listing executions: {str(e)}", 500)

async def get_execution(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        execution_id = message.get("payload", {}).get("execution_id")
        if not execution_id:
            return create_mcp_error_response(message, "Execution ID is required", 400)
        
        # Récupérer l'exécution de la base de données
        execution = executions_collection.find_one({"id": execution_id}, {"_id": 0})
        if not execution:
            return create_mcp_error_response(message, f"Execution with ID {execution_id} not found", 404)
        
        return create_mcp_response(message, {"execution": execution})
    
    except Exception as e:
        print(f"Error getting execution: {str(e)}")
        return create_mcp_error_response(message, f"Error getting execution: {str(e)}", 500)

async def create_execution(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        execution_data = message.get("payload", {}).get("execution", {})
        if not execution_data:
            return create_mcp_error_response(message, "Execution data is required", 400)
        
        # Vérifier que le déploiement est spécifié
        deployment_id = execution_data.get("deployment_id")
        if not deployment_id:
            return create_mcp_error_response(message, "Deployment ID is required for execution", 400)
        
        # Vérifier si le déploiement existe
        deployment = deployments_collection.find_one({"id": deployment_id})
        if not deployment:
            return create_mcp_error_response(message, f"Deployment with ID {deployment_id} not found", 404)
        
        # Vérifier si le déploiement est actif
        if deployment.get("status") != "active":
            return create_mcp_error_response(message, f"Deployment with ID {deployment_id} is not active", 400)
        
        # Générer un ID unique si non fourni
        if "id" not in execution_data:
            execution_data["id"] = str(uuid.uuid4())
        
        # Ajouter des informations supplémentaires
        execution_data["model_id"] = deployment.get("model_id")
        execution_data["model_name"] = deployment.get("model_name", "Unknown Model")
        execution_data["deployment_name"] = deployment.get("name", "Unknown Deployment")
        execution_data["status"] = "pending"
        execution_data["started_at"] = datetime.now().isoformat()
        execution_data["updated_at"] = execution_data["started_at"]
        
        # Insérer l'exécution dans la base de données
        executions_collection.insert_one(execution_data)
        
        # Dans un système réel, nous lancerions ici l'exécution de manière asynchrone
        # Pour ce POC, nous simulons une exécution réussie
        
        # Simuler l'utilisation de Groq pour l'inférence
        if groq_client:
            # Simuler une réponse Groq
            execution_data["groq_response"] = {
                "model": "llama3-70b-8192",
                "status": "success",
                "tokens_generated": 512
            }
        
        # Créer un résultat d'exécution simulé
        result_data = {
            "execution_id": execution_data["id"],
            "predictions": [
                {"label": "Class A", "probability": 0.85},
                {"label": "Class B", "probability": 0.12},
                {"label": "Class C", "probability": 0.03}
            ],
            "metrics": {
                "accuracy": 0.92,
                "precision": 0.89,
                "recall": 0.94,
                "f1_score": 0.91
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Stocker les résultats dans MinIO
        result_path = f"{execution_data['id']}/results.json"
        try:
            import json
            import io
            
            result_json = json.dumps(result_data, indent=2)
            result_bytes = result_json.encode('utf-8')
            result_stream = io.BytesIO(result_bytes)
            
            minio_client.put_object(
                RESULTS_BUCKET,
                result_path,
                result_stream,
                len(result_bytes),
                content_type="application/json"
            )
            
            # Mettre à jour l'exécution avec le chemin des résultats et changer le statut
            execution_data["result_path"] = result_path
            execution_data["status"] = "completed"
            execution_data["completed_at"] = datetime.now().isoformat()
            execution_data["updated_at"] = execution_data["completed_at"]
            
            # Mettre à jour l'exécution dans la base de données
            executions_collection.update_one(
                {"id": execution_data["id"]},
                {"$set": execution_data}
            )
            
        except S3Error as e:
            # En cas d'erreur lors du stockage des résultats, marquer l'exécution comme échouée
            execution_data["status"] = "failed"
            execution_data["error"] = f"Error storing results: {str(e)}"
            execution_data["updated_at"] = datetime.now().isoformat()
            
            executions_collection.update_one(
                {"id": execution_data["id"]},
                {"$set": execution_data}
            )
            
            return create_mcp_error_response(message, f"Error storing execution results: {str(e)}", 500)
        
        return create_mcp_response(message, {"execution": execution_data})
    
    except Exception as e:
        print(f"Error creating execution: {str(e)}")
        return create_mcp_error_response(message, f"Error creating execution: {str(e)}", 500)

async def cancel_execution(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        execution_id = message.get("payload", {}).get("execution_id")
        if not execution_id:
            return create_mcp_error_response(message, "Execution ID is required", 400)
        
        # Vérifier si l'exécution existe
        execution = executions_collection.find_one({"id": execution_id})
        if not execution:
            return create_mcp_error_response(message, f"Execution with ID {execution_id} not found", 404)
        
        # Vérifier si l'exécution peut être annulée
        if execution.get("status") not in ["pending", "running"]:
            return create_mcp_error_response(
                message, 
                f"Cannot cancel execution with status '{execution.get('status')}'. Only pending or running executions can be cancelled.", 
                400
            )
        
        # Mettre à jour le statut de l'exécution
        updated_data = {
            "status": "cancelled",
            "cancelled_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        executions_collection.update_one(
            {"id": execution_id},
            {"$set": updated_data}
        )
        
        # Récupérer l'exécution mise à jour
        updated_execution = executions_collection.find_one({"id": execution_id}, {"_id": 0})
        
        return create_mcp_response(message, {
            "message": f"Execution with ID {execution_id} cancelled successfully",
            "execution": updated_execution
        })
    
    except Exception as e:
        print(f"Error cancelling execution: {str(e)}")
        return create_mcp_error_response(message, f"Error cancelling execution: {str(e)}", 500)

async def get_execution_results(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        execution_id = message.get("payload", {}).get("execution_id")
        if not execution_id:
            return create_mcp_error_response(message, "Execution ID is required", 400)
        
        # Vérifier si l'exécution existe
        execution = executions_collection.find_one({"id": execution_id}, {"_id": 0})
        if not execution:
            return create_mcp_error_response(message, f"Execution with ID {execution_id} not found", 404)
        
        # Vérifier si l'exécution est terminée et a des résultats
        if execution.get("status") != "completed":
            return create_mcp_error_response(
                message,
                f"Execution with ID {execution_id} is not completed. Current status: {execution.get('status')}",
                400
            )
        
        # Vérifier si un chemin de résultat est disponible
        result_path = execution.get("result_path")
        if not result_path:
            return create_mcp_error_response(
                message,
                f"Execution with ID {execution_id} has no result path available",
                404
            )
        
        # Récupérer les résultats depuis MinIO
        try:
            import json
            
            # Récupérer l'objet depuis MinIO
            response = minio_client.get_object(RESULTS_BUCKET, result_path)
            results_data = json.loads(response.read().decode('utf-8'))
            
            return create_mcp_response(message, {
                "execution_id": execution_id,
                "results": results_data
            })
            
        except S3Error as e:
            return create_mcp_error_response(
                message,
                f"Error retrieving results from storage: {str(e)}",
                500
            )
    
    except Exception as e:
        print(f"Error getting execution results: {str(e)}")
        return create_mcp_error_response(message, f"Error getting execution results: {str(e)}", 500)
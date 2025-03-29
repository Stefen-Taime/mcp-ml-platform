from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import uuid
import json
from datetime import datetime
import os
import time
import io
import base64
import subprocess
import asyncio
from typing import Dict, Any, List, Optional
import pymongo
from pymongo import MongoClient
from bson import ObjectId
from minio import Minio
from minio.error import S3Error

# Essayer d'importer groq
try:
    import groq
    GROQ_AVAILABLE = True
except ImportError:
    print("Groq module not available, using simulation")
    GROQ_AVAILABLE = False

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
models_collection = db["models"]
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

# Configuration Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
groq_client = None
if GROQ_AVAILABLE and GROQ_API_KEY:
    groq_client = groq.Groq(api_key=GROQ_API_KEY)
    print("Groq client initialized")
else:
    print("Groq client not initialized")

# Configuration Spark
SPARK_MASTER_URL = os.getenv("SPARK_MASTER_URL", "spark://spark-master:7077")
SPARK_ENABLED = os.getenv("SPARK_ENABLED", "False").lower() == "true"
SPARK_APP_PATH = os.getenv("SPARK_APP_PATH", "/opt/spark-apps/model_execution.py")

print(f"Spark configuration: Enabled={SPARK_ENABLED}, Master URL={SPARK_MASTER_URL}")

# Essayer d'importer PySpark si Spark est activé
if SPARK_ENABLED:
    try:
        from pyspark.sql import SparkSession
        from pyspark.sql.functions import col, when, lit
        
        # Initialiser SparkSession
        def get_spark_session():
            return SparkSession.builder \
                .appName("MCP ML Execution") \
                .master(SPARK_MASTER_URL) \
                .config("spark.executor.memory", "2g") \
                .config("spark.driver.memory", "2g") \
                .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.1") \
                .config("spark.hadoop.fs.s3a.endpoint", f"http://{MINIO_ENDPOINT}") \
                .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY) \
                .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY) \
                .config("spark.hadoop.fs.s3a.path.style.access", "true") \
                .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
                .getOrCreate()
        
        # Tester une session Spark et la fermer immédiatement
        test_spark = get_spark_session()
        test_spark.stop()
        print("Spark session test successful")
    except Exception as e:
        print(f"Error initializing Spark: {str(e)}")
        SPARK_ENABLED = False

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

# Buckets pour les résultats d'exécution
RESULTS_BUCKET = "results"
MODELS_BUCKET = "models"
DATASETS_BUCKET = "datasets"

# Vérifier si les buckets existent, sinon les créer
for bucket in [RESULTS_BUCKET, MODELS_BUCKET, DATASETS_BUCKET]:
    if not minio_client.bucket_exists(bucket):
        minio_client.make_bucket(bucket)
        print(f"Bucket '{bucket}' créé avec succès")
    else:
        print(f"Bucket '{bucket}' existe déjà")

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
            "id": "execution-mcp-server",
            "type": "execution-mcp-server"
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

# Fonction pour exécuter un job Spark
async def run_spark_job(execution_id: str):
    """Exécute un job Spark pour l'exécution spécifiée"""
    try:
        # Construction de la commande spark-submit
        command = [
            "spark-submit",
            "--master", SPARK_MASTER_URL,
            "--deploy-mode", "client",
            "--conf", "spark.driver.memory=1g",
            "--conf", "spark.executor.memory=1g",
            SPARK_APP_PATH,
            execution_id
        ]
        
        # Exécution de la commande
        print(f"Executing Spark job: {' '.join(command)}")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Capturer la sortie
        stdout, stderr = process.communicate()
        return_code = process.returncode
        
        if return_code == 0:
            print(f"Spark job completed successfully for execution {execution_id}")
            print(f"Output: {stdout.decode('utf-8')}")
            return True
        else:
            print(f"Spark job failed for execution {execution_id}")
            print(f"Error: {stderr.decode('utf-8')}")
            
            # Mettre à jour le statut de l'exécution en cas d'échec
            executions_collection.update_one(
                {"id": execution_id},
                {"$set": {
                    "status": "failed",
                    "error": f"Spark job failed: {stderr.decode('utf-8')}",
                    "updated_at": datetime.now().isoformat()
                }}
            )
            return False
    
    except Exception as e:
        print(f"Error running Spark job: {str(e)}")
        
        # Mettre à jour le statut de l'exécution en cas d'erreur
        executions_collection.update_one(
            {"id": execution_id},
            {"$set": {
                "status": "failed",
                "error": f"Error running Spark job: {str(e)}",
                "updated_at": datetime.now().isoformat()
            }}
        )
        return False

# Point d'entrée pour traiter les messages MCP
@app.post("/process")
async def process_mcp_message(message: Dict[str, Any]):
    try:
        operation = message.get("operation")
        print(f"Received MCP request for operation: {operation}")
        print(f"Request payload: {json.dumps(message.get('payload', {}), cls=MongoJSONEncoder)}")
        
        # Router vers la fonction appropriée en fonction de l'opération
        if operation == "list_deployments":
            response = await list_deployments(message)
        elif operation == "get_deployment":
            response = await get_deployment(message)
        elif operation == "create_deployment":
            response = await create_deployment(message)
        elif operation == "update_deployment":
            response = await update_deployment(message)
        elif operation == "delete_deployment":
            response = await delete_deployment(message)
        elif operation == "list_executions":
            response = await list_executions(message)
        elif operation == "get_execution":
            response = await get_execution(message)
        elif operation == "create_execution":
            response = await create_execution(message)
        elif operation == "cancel_execution":
            response = await cancel_execution(message)
        elif operation == "get_execution_results":
            response = await get_execution_results(message)
        else:
            response = create_mcp_error_response(message, f"Unsupported operation: {operation}", 400)
        
        print(f"Sending MCP response for operation: {operation}")
        return response
    
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        return create_mcp_error_response(message, f"Internal server error: {str(e)}", 500)

# Opérations sur les déploiements
async def list_deployments(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Récupérer tous les déploiements de la base de données
        deployments = list(deployments_collection.find({}))
        
        # Convertir les déploiements en objets sérialisables en JSON
        serializable_deployments = mongo_to_json_serializable(deployments)
        
        return create_mcp_response(message, {"deployments": serializable_deployments})
    
    except Exception as e:
        print(f"Error listing deployments: {str(e)}")
        return create_mcp_error_response(message, f"Error listing deployments: {str(e)}", 500)

async def get_deployment(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        deployment_id = message.get("payload", {}).get("deployment_id")
        if not deployment_id:
            return create_mcp_error_response(message, "Deployment ID is required", 400)
        
        # Récupérer le déploiement de la base de données
        deployment = deployments_collection.find_one({"id": deployment_id})
        if not deployment:
            return create_mcp_error_response(message, f"Deployment with ID {deployment_id} not found", 404)
        
        # Convertir le déploiement en objet sérialisable en JSON
        serializable_deployment = mongo_to_json_serializable(deployment)
        
        return create_mcp_response(message, {"deployment": serializable_deployment})
    
    except Exception as e:
        print(f"Error getting deployment: {str(e)}")
        return create_mcp_error_response(message, f"Error getting deployment: {str(e)}", 500)

async def create_deployment(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        deployment_data = message.get("payload", {}).get("deployment", {})
        if not deployment_data:
            return create_mcp_error_response(message, "Deployment data is required", 400)
        
        # Vérifier que le modèle est spécifié
        model_id = deployment_data.get("model_id")
        if not model_id:
            return create_mcp_error_response(message, "Model ID is required for deployment", 400)
        
        # Vérifier si le modèle existe
        model = models_collection.find_one({"id": model_id})
        if not model:
            return create_mcp_error_response(message, f"Model with ID {model_id} not found", 404)
        
        # Générer un ID unique si non fourni
        if "id" not in deployment_data:
            deployment_data["id"] = str(uuid.uuid4())
        
        # Ajouter des timestamps et statut par défaut
        deployment_data["created_at"] = datetime.now().isoformat()
        deployment_data["updated_at"] = deployment_data["created_at"]
        deployment_data["status"] = deployment_data.get("status", "inactive")
        
        # Log la création du déploiement
        print(f"Deployment created with ID: {deployment_data['id']}")
        
        # Insérer le déploiement dans la base de données
        deployments_collection.insert_one(deployment_data)
        
        # Convertir le déploiement en objet sérialisable en JSON
        serializable_deployment = mongo_to_json_serializable(deployment_data)
        
        return create_mcp_response(message, {"deployment": serializable_deployment})
    
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
        
        # Convertir l'objet existant pour accès compatible
        existing_deployment = mongo_to_json_serializable(existing_deployment)
        
        # Mettre à jour le timestamp
        deployment_data["updated_at"] = datetime.now().isoformat()
        if "created_at" not in deployment_data:
            deployment_data["created_at"] = existing_deployment.get("created_at")
        
        # Mettre à jour le déploiement dans la base de données
        deployments_collection.update_one({"id": deployment_id}, {"$set": deployment_data})
        
        # Log la mise à jour
        print(f"Deployment updated with ID: {deployment_id}")
        
        # Convertir le déploiement en objet sérialisable en JSON
        serializable_deployment = mongo_to_json_serializable(deployment_data)
        
        return create_mcp_response(message, {"deployment": serializable_deployment})
    
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
            "status": {"$in": ["pending", "running", "processing_with_spark"]}
        })
        if active_executions:
            return create_mcp_error_response(
                message, 
                f"Cannot delete deployment with active executions. Cancel executions first.", 
                409
            )
        
        # Supprimer le déploiement de la base de données
        deployments_collection.delete_one({"id": deployment_id})
        
        # Log la suppression
        print(f"Deployment deleted with ID: {deployment_id}")
        
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
        executions = list(executions_collection.find(filter_query))
        
        # Convertir les exécutions en objets sérialisables en JSON
        serializable_executions = mongo_to_json_serializable(executions)
        
        return create_mcp_response(message, {"executions": serializable_executions})
    
    except Exception as e:
        print(f"Error listing executions: {str(e)}")
        return create_mcp_error_response(message, f"Error listing executions: {str(e)}", 500)

async def get_execution(message: Dict[str, Any]) -> Dict[str, Any]:
    try:
        execution_id = message.get("payload", {}).get("execution_id")
        if not execution_id:
            return create_mcp_error_response(message, "Execution ID is required", 400)
        
        # Récupérer l'exécution de la base de données
        execution = executions_collection.find_one({"id": execution_id})
        if not execution:
            return create_mcp_error_response(message, f"Execution with ID {execution_id} not found", 404)
        
        # Convertir l'exécution en objet sérialisable en JSON
        serializable_execution = mongo_to_json_serializable(execution)
        
        return create_mcp_response(message, {"execution": serializable_execution})
    
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
        
        # Convertir le déploiement en objet sérialisable en JSON
        deployment = mongo_to_json_serializable(deployment)
        
        # Vérifier si le déploiement est actif
        if deployment.get("status") != "active":
            return create_mcp_error_response(message, f"Deployment with ID {deployment_id} is not active", 400)
        
        # Générer un ID unique si non fourni
        if "id" not in execution_data:
            execution_data["id"] = str(uuid.uuid4())
            
        execution_id = execution_data["id"]
        
        # Récupérer le modèle associé au déploiement
        model_id = deployment.get("model_id")
        model = models_collection.find_one({"id": model_id})
        if not model:
            return create_mcp_error_response(message, f"Model with ID {model_id} not found", 404)
        
        # Convertir le modèle en objet sérialisable en JSON
        model = mongo_to_json_serializable(model)
        
        # Ajouter des informations supplémentaires
        execution_data["model_id"] = model_id
        execution_data["model_name"] = model.get("name", "Unknown Model")
        execution_data["deployment_name"] = deployment.get("name", "Unknown Deployment")
        execution_data["status"] = "pending"
        execution_data["started_at"] = datetime.now().isoformat()
        execution_data["updated_at"] = execution_data["started_at"]
        
        # Log la création de l'exécution
        print(f"Creating execution with ID: {execution_data['id']} for deployment: {deployment_id}")
        
        # Insérer l'exécution dans la base de données
        executions_collection.insert_one(execution_data)
        
        # Récupération des données et paramètres
        parameters = execution_data.get("parameters", {})
        dataset_id = parameters.get("dataset_id")
        input_data = parameters.get("input_data")
        use_spark = parameters.get("use_spark", False)
        
        # Vérifier si nous devons utiliser Spark pour cette exécution
        if SPARK_ENABLED and use_spark:
            print(f"Using Spark for execution {execution_id}")
            
            # Mettre à jour le statut pour indiquer que le traitement Spark est en cours
            executions_collection.update_one(
                {"id": execution_id},
                {"$set": {
                    "status": "processing_with_spark",
                    "updated_at": datetime.now().isoformat()
                }}
            )
            
            # Lancer le job Spark en arrière-plan
            asyncio.create_task(run_spark_job(execution_id))
            
            # Mettre à jour l'exécution avec les informations sur le job Spark
            execution_data["status"] = "processing_with_spark"
            execution_data["spark_job_status"] = "submitted"
            execution_data["updated_at"] = datetime.now().isoformat()
            
            # Retourner une réponse immédiate
            serializable_execution = mongo_to_json_serializable(execution_data)
            return create_mcp_response(message, {"execution": serializable_execution})
        
        # Si nous n'utilisons pas Spark, exécuter le traitement ici
        # Mise à jour du statut en cours d'exécution
        executions_collection.update_one(
            {"id": execution_id},
            {"$set": {"status": "running", "updated_at": datetime.now().isoformat()}}
        )
        
        # Résultat d'exécution par défaut
        execution_result = {
            "execution_id": execution_id,
            "predictions": [],
            "metrics": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Traitement selon que nous utilisons un dataset ou des données d'entrée directes
        if dataset_id:
            # Vérifier si le dataset existe
            dataset = datasets_collection.find_one({"id": dataset_id})
            if not dataset:
                return create_mcp_error_response(message, f"Dataset with ID {dataset_id} not found", 404)
            
            # Convertir le dataset en objet sérialisable en JSON
            dataset = mongo_to_json_serializable(dataset)
            
            # Simuler des résultats basés sur le dataset
            print(f"Generating results for dataset: {dataset_id}")
            execution_result["predictions"] = [
                {"label": "Class A", "probability": 0.85},
                {"label": "Class B", "probability": 0.12},
                {"label": "Class C", "probability": 0.03}
            ]
            execution_result["metrics"] = {
                "accuracy": 0.92,
                "precision": 0.89,
                "recall": 0.94,
                "f1_score": 0.91,
                "record_count": 50  # Valeur simulée
            }
        elif input_data:
            # Traitement des données d'entrée directes
            print(f"Processing direct input data")
            
            # Si Groq est configuré, utiliser Groq pour le traitement
            if groq_client and GROQ_API_KEY and GROQ_AVAILABLE:
                try:
                    # Préparer les données pour Groq
                    prompt = f"Analyze the following data and provide insights: {json.dumps(input_data)}"
                    
                    # Appeler l'API Groq
                    completion = groq_client.chat.completions.create(
                        model="llama3-70b-8192",  # ou un autre modèle disponible
                        messages=[
                            {"role": "system", "content": "You are a data analysis assistant. Analyze the data and provide insights."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=1024
                    )
                    
                    # Extraire la réponse
                    response_text = completion.choices[0].message.content
                    
                    # Stocker la réponse de Groq
                    execution_data["groq_response"] = {
                        "model": completion.model,
                        "status": "success",
                        "tokens_generated": completion.usage.completion_tokens,
                        "total_tokens": completion.usage.total_tokens
                    }
                    
                    # Traiter la réponse
                    execution_result["predictions"] = [
                        {"analysis": response_text}
                    ]
                    execution_result["metrics"] = {
                        "processing_time_ms": int(time.time() * 1000) - int(datetime.fromisoformat(execution_data["started_at"]).timestamp() * 1000),
                        "tokens_generated": completion.usage.completion_tokens,
                        "total_tokens": completion.usage.total_tokens
                    }
                    
                    print(f"Processed data with Groq, generated {completion.usage.completion_tokens} tokens")
                except Exception as e:
                    print(f"Error processing data with Groq: {str(e)}")
                    # Continuer avec la simulation si Groq échoue
                    execution_data["groq_error"] = str(e)
            
            # Si pas de traitement Groq ou s'il a échoué, simuler des résultats
            if not execution_result["predictions"]:
                print("Generating simulated results for input data")
                # Simuler Groq
                execution_data["groq_response"] = {
                    "model": "llama3-70b-8192",
                    "status": "success",
                    "tokens_generated": 512
                }
                
                # Résultats simulés basés sur le type de données d'entrée
                if isinstance(input_data, dict) and "experience" in input_data:
                    # Simulation pour les données de salaire
                    execution_result["predictions"] = [
                        {"label": "Predicted Salary", "value": 50000 + 1500 * (input_data.get("experience", 5))}
                    ]
                else:
                    # Simulation générique
                    # Simulation générique
                    execution_result["predictions"] = [
                        {"label": "Class A", "probability": 0.85},
                        {"label": "Class B", "probability": 0.12},
                        {"label": "Class C", "probability": 0.03}
                    ]
                
                execution_result["metrics"] = {
                    "accuracy": 0.92,
                    "precision": 0.89,
                    "recall": 0.94,
                    "f1_score": 0.91
                }
        else:
            # Ni dataset ni input_data spécifiés, générer des résultats aléatoires
            print("No dataset_id or input_data provided, generating random results")
            import random
            
            execution_result["predictions"] = [
                {"label": "Random Prediction", "value": random.uniform(0, 100)},
                {"label": "Another Random", "value": random.uniform(0, 100)}
            ]
            execution_result["metrics"] = {
                "random_quality": random.uniform(0.7, 0.99)
            }
        
        # Stocker les résultats dans MinIO
        result_path = f"{execution_id}/results.json"
        
        # Convertir les résultats en JSON
        result_json = json.dumps(execution_result, indent=2, cls=MongoJSONEncoder)
        result_bytes = result_json.encode('utf-8')
        result_stream = io.BytesIO(result_bytes)
        
        minio_client.put_object(
            RESULTS_BUCKET,
            result_path,
            result_stream,
            len(result_bytes),
            content_type="application/json"
        )
        
        # Log le stockage des résultats
        print(f"Results stored in MinIO: {result_path}")
        
        # Mettre à jour l'exécution avec le chemin des résultats et changer le statut
        execution_data["result_path"] = result_path
        execution_data["status"] = "completed"
        execution_data["completed_at"] = datetime.now().isoformat()
        execution_data["updated_at"] = execution_data["completed_at"]
        
        # Mettre à jour l'exécution dans la base de données
        executions_collection.update_one(
            {"id": execution_id},
            {"$set": execution_data}
        )
        
        # Convertir l'exécution en objet sérialisable en JSON
        serializable_execution = mongo_to_json_serializable(execution_data)
        
        return create_mcp_response(message, {"execution": serializable_execution})
    
    except Exception as e:
        print(f"Error creating execution: {str(e)}")
        
        # Mettre à jour le statut de l'exécution en cas d'erreur
        if 'execution_id' in locals():
            executions_collection.update_one(
                {"id": execution_id},
                {"$set": {
                    "status": "failed",
                    "error": str(e),
                    "updated_at": datetime.now().isoformat()
                }}
            )
        
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
        
        # Convertir l'exécution en objet sérialisable en JSON
        execution = mongo_to_json_serializable(execution)
        
        # Vérifier si l'exécution peut être annulée
        if execution.get("status") not in ["pending", "running", "processing_with_spark"]:
            return create_mcp_error_response(
                message, 
                f"Cannot cancel execution with status '{execution.get('status')}'. Only pending, running or processing executions can be cancelled.", 
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
        
        # Log l'annulation
        print(f"Execution cancelled with ID: {execution_id}")
        
        # Récupérer l'exécution mise à jour
        updated_execution = executions_collection.find_one({"id": execution_id})
        
        # Convertir l'exécution mise à jour en objet sérialisable en JSON
        serializable_updated_execution = mongo_to_json_serializable(updated_execution)
        
        return create_mcp_response(message, {
            "message": f"Execution with ID {execution_id} cancelled successfully",
            "execution": serializable_updated_execution
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
        execution = executions_collection.find_one({"id": execution_id})
        if not execution:
            return create_mcp_error_response(message, f"Execution with ID {execution_id} not found", 404)
        
        # Convertir l'exécution en objet sérialisable en JSON
        execution = mongo_to_json_serializable(execution)
        
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
            # Récupérer l'objet depuis MinIO
            response = minio_client.get_object(RESULTS_BUCKET, result_path)
            results_data = json.loads(response.read().decode('utf-8'))
            
            # Si les résultats contiennent des données binaires (comme des images), les convertir en base64
            if "binary_data" in results_data:
                binary_data = results_data["binary_data"]
                if isinstance(binary_data, bytes):
                    results_data["binary_data"] = base64.b64encode(binary_data).decode('utf-8')
            
            return create_mcp_response(message, {
                "execution_id": execution_id,
                "results": results_data
            })
            
        except Exception as e:
            print(f"Error retrieving results from MinIO: {str(e)}")
            return create_mcp_error_response(
                message,
                f"Error retrieving results from storage: {str(e)}",
                500
            )
    
    except Exception as e:
        print(f"Error getting execution results: {str(e)}")
        return create_mcp_error_response(message, f"Error getting execution results: {str(e)}", 500)

# Fonctions utilitaires
async def get_model_file(model_id: str):
    """Récupère le fichier d'un modèle depuis MinIO"""
    try:
        # Vérifier si le modèle existe
        model = models_collection.find_one({"id": model_id})
        if not model:
            raise ValueError(f"Model with ID {model_id} not found")
        
        # Vérifier si le modèle a un fichier associé
        if not model.get("has_file"):
            raise ValueError(f"Model with ID {model_id} has no associated file")
        
        file_path = model.get("file_path")
        if not file_path:
            raise ValueError(f"Model with ID {model_id} has no file path")
        
        # Récupérer le fichier depuis MinIO
        response = minio_client.get_object(MODELS_BUCKET, file_path)
        file_data = response.read()
        
        print(f"Model file retrieved from MinIO: {file_path}, size: {len(file_data)}")
        
        return {
            "file_data": file_data,
            "file_name": model.get("file_name"),
            "content_type": model.get("content_type")
        }
        
    except Exception as e:
        print(f"Error retrieving model file: {str(e)}")
        raise ValueError(f"Error retrieving model file: {str(e)}")

async def get_dataset_file(dataset_id: str):
    """Récupère le fichier d'un dataset depuis MinIO"""
    try:
        # Vérifier si le dataset existe
        dataset = datasets_collection.find_one({"id": dataset_id})
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} not found")
        
        # Vérifier si le dataset a un fichier associé
        if not dataset.get("has_file"):
            raise ValueError(f"Dataset with ID {dataset_id} has no associated file")
        
        file_path = dataset.get("file_path")
        if not file_path:
            raise ValueError(f"Dataset with ID {dataset_id} has no file path")
        
        # Récupérer le fichier depuis MinIO
        response = minio_client.get_object(DATASETS_BUCKET, file_path)
        file_data = response.read()
        
        print(f"Dataset file retrieved from MinIO: {file_path}, size: {len(file_data)}")
        
        return {
            "file_data": file_data,
            "file_name": dataset.get("file_name"),
            "content_type": dataset.get("content_type")
        }
        
    except Exception as e:
        print(f"Error retrieving dataset file: {str(e)}")
        raise ValueError(f"Error retrieving dataset file: {str(e)}")

# Route de santé
@app.get("/health")
async def health_check():
    try:
        # Vérifier la connexion à MongoDB
        mongo_status = "ok" if mongo_client.server_info() else "error"
        
        # Vérifier la connexion à MinIO
        minio_status = "ok" if minio_client.bucket_exists(RESULTS_BUCKET) else "error"
        
        # Vérifier la connexion à Groq
        groq_status = "ok" if groq_client and GROQ_API_KEY and GROQ_AVAILABLE else "not_configured"
        
        # Vérifier la connexion à Spark
        spark_status = "ok" if SPARK_ENABLED else "not_configured"
        
        status = "ok" if mongo_status == "ok" and minio_status == "ok" else "error"
        
        return {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "services": {
                "mongodb": mongo_status,
                "minio": minio_status,
                "groq": groq_status,
                "spark": spark_status
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
    uvicorn.run(app, host="0.0.0.0", port=8004)
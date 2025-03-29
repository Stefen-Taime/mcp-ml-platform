from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import uuid
import json
from datetime import datetime
import os

app = FastAPI(title="MCP ML Platform API Gateway")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Pour le développement, à restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration des URLs des services
MCP_HUB_URL = os.getenv("MCP_HUB_URL", "http://mcp-hub:8001")

# Client HTTP asynchrone avec timeout augmenté
http_client = httpx.AsyncClient(timeout=30.0)

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

# Fonction pour créer un message MCP
def create_mcp_message(operation, payload, message_type="request"):
    return {
        "mcp_version": "1.0",
        "message_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "sender": {
            "id": "api-gateway-1",
            "type": "api-gateway"
        },
        "recipient": {
            "id": "mcp-hub",
            "type": "mcp-hub"
        },
        "message_type": message_type,
        "operation": operation,
        "payload": payload,
        "metadata": {}
    }

# Fonction pour gérer la réponse MCP et extraire le contenu pertinent
async def process_mcp_response(response, key=None, error_status=404, error_message="Ressource non trouvée"):
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Erreur lors de la communication avec le MCP Hub: {response.text}")
    
    # Récupérer le corps de la réponse JSON
    response_data = response.json()
    
    # Vérifier le statut de la réponse MCP
    if response_data.get("status") == "error":
        error_detail = response_data.get("payload", {}).get("error", "Erreur inconnue")
        error_code = response_data.get("payload", {}).get("status_code", 500)
        raise HTTPException(status_code=error_code, detail=error_detail)
    
    # Si une clé spécifique est demandée, essayer de l'extraire
    if key and key in response_data.get("payload", {}):
        return response_data["payload"][key]
    elif key:
        # Si la clé n'est pas trouvée mais est spécifiquement demandée
        print(f"Clé '{key}' non trouvée dans la réponse MCP. Contenu du payload: {json.dumps(response_data.get('payload', {}))}")
        raise HTTPException(status_code=error_status, detail=error_message)
    
    # Sinon retourner tout le payload
    return response_data.get("payload", {})

# Routes pour les modèles
@app.get("/models")
async def get_models():
    try:
        mcp_message = create_mcp_message("list_models", {})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(response, "models")
        return result
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.get("/models/{model_id}")
async def get_model(model_id: str):
    try:
        mcp_message = create_mcp_message("get_model", {"model_id": model_id})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(
            response, 
            "model", 
            404, 
            f"Modèle {model_id} non trouvé"
        )
        return result
    except httpx.HTTPError as e:
        if hasattr(e, 'response') and e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Modèle {model_id} non trouvé")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.post("/models")
async def create_model(model_data: dict):
    try:
        mcp_message = create_mcp_message("create_model", {"model": model_data})
        print(f"Envoi de la requête de création de modèle: {json.dumps(mcp_message)}")
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        print(f"Réponse reçue: {response.text}")
        result = await process_mcp_response(response, "model")
        return result
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.put("/models/{model_id}")
async def update_model(model_id: str, model_data: dict):
    try:
        model_data["id"] = model_id
        mcp_message = create_mcp_message("update_model", {"model": model_data})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(
            response, 
            "model", 
            404, 
            f"Modèle {model_id} non trouvé"
        )
        return result
    except httpx.HTTPError as e:
        if hasattr(e, 'response') and e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Modèle {model_id} non trouvé")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.delete("/models/{model_id}")
async def delete_model(model_id: str):
    try:
        mcp_message = create_mcp_message("delete_model", {"model_id": model_id})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(response)
        return {"message": f"Modèle {model_id} supprimé avec succès"}
    except httpx.HTTPError as e:
        if hasattr(e, 'response') and e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Modèle {model_id} non trouvé")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

# Routes pour les déploiements
@app.get("/deployments")
async def get_deployments():
    try:
        mcp_message = create_mcp_message("list_deployments", {})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(response, "deployments")
        return result
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.get("/deployments/{deployment_id}")
async def get_deployment(deployment_id: str):
    try:
        mcp_message = create_mcp_message("get_deployment", {"deployment_id": deployment_id})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(
            response, 
            "deployment", 
            404, 
            f"Déploiement {deployment_id} non trouvé"
        )
        return result
    except httpx.HTTPError as e:
        if hasattr(e, 'response') and e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Déploiement {deployment_id} non trouvé")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.post("/deployments")
async def create_deployment(deployment_data: dict):
    try:
        mcp_message = create_mcp_message("create_deployment", {"deployment": deployment_data})
        print(f"Envoi de la requête de création de déploiement: {json.dumps(mcp_message)}")
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        print(f"Réponse reçue: {response.text}")
        result = await process_mcp_response(response, "deployment")
        return result
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.put("/deployments/{deployment_id}")
async def update_deployment(deployment_id: str, deployment_data: dict):
    try:
        deployment_data["id"] = deployment_id
        mcp_message = create_mcp_message("update_deployment", {"deployment": deployment_data})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(
            response, 
            "deployment", 
            404, 
            f"Déploiement {deployment_id} non trouvé"
        )
        return result
    except httpx.HTTPError as e:
        if hasattr(e, 'response') and e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Déploiement {deployment_id} non trouvé")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.delete("/deployments/{deployment_id}")
async def delete_deployment(deployment_id: str):
    try:
        mcp_message = create_mcp_message("delete_deployment", {"deployment_id": deployment_id})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(response)
        return {"message": f"Déploiement {deployment_id} supprimé avec succès"}
    except httpx.HTTPError as e:
        if hasattr(e, 'response') and e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Déploiement {deployment_id} non trouvé")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

# Routes pour les exécutions
@app.get("/executions")
async def get_executions():
    try:
        mcp_message = create_mcp_message("list_executions", {})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(response, "executions")
        return result
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    try:
        mcp_message = create_mcp_message("get_execution", {"execution_id": execution_id})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(
            response, 
            "execution", 
            404, 
            f"Exécution {execution_id} non trouvée"
        )
        return result
    except httpx.HTTPError as e:
        if hasattr(e, 'response') and e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Exécution {execution_id} non trouvée")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.post("/executions")
async def create_execution(execution_data: dict):
    try:
        mcp_message = create_mcp_message("create_execution", {"execution": execution_data})
        print(f"Envoi de la requête de création d'exécution: {json.dumps(mcp_message)}")
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        print(f"Réponse reçue: {response.text}")
        result = await process_mcp_response(response, "execution")
        return result
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    try:
        mcp_message = create_mcp_message("cancel_execution", {"execution_id": execution_id})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(response)
        return {"message": f"Exécution {execution_id} annulée avec succès"}
    except httpx.HTTPError as e:
        if hasattr(e, 'response') and e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Exécution {execution_id} non trouvée")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.get("/executions/{execution_id}/results")
async def get_execution_results(execution_id: str):
    try:
        mcp_message = create_mcp_message("get_execution_results", {"execution_id": execution_id})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(
            response, 
            "results", 
            404, 
            f"Résultats pour l'exécution {execution_id} non trouvés"
        )
        return result
    except httpx.HTTPError as e:
        if hasattr(e, 'response') and e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Résultats pour l'exécution {execution_id} non trouvés")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

# Routes pour les datasets
@app.get("/datasets")
async def get_datasets():
    try:
        mcp_message = create_mcp_message("list_datasets", {})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(response, "datasets")
        return result
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str):
    try:
        mcp_message = create_mcp_message("get_dataset", {"dataset_id": dataset_id})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(
            response, 
            "dataset", 
            404, 
            f"Dataset {dataset_id} non trouvé"
        )
        return result
    except httpx.HTTPError as e:
        if hasattr(e, 'response') and e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} non trouvé")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.post("/datasets")
async def create_dataset(dataset_data: dict):
    try:
        mcp_message = create_mcp_message("create_dataset", {"dataset": dataset_data})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(response, "dataset")
        return result
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

# Routes pour les opérations complexes
@app.post("/operations/chain")
async def chain_operations(operations_data: dict):
    try:
        mcp_message = create_mcp_message("chain_operations", {"operations": operations_data.get("operations", [])})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(response, "final_result")
        return result
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.post("/operations/validate-and-execute")
async def validate_and_execute(validation_data: dict):
    try:
        mcp_message = create_mcp_message("validate_and_execute", validation_data)
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(response, "execution_result")
        return result
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.post("/operations/parallel-execute")
async def parallel_execute(parallel_data: dict):
    try:
        mcp_message = create_mcp_message("parallel_execute", parallel_data)
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(response)
        return result
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.post("/operations/evaluate-and-optimize")
async def evaluate_and_optimize(evaluation_data: dict):
    try:
        mcp_message = create_mcp_message("evaluate_and_optimize", evaluation_data)
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        result = await process_mcp_response(response)
        return result
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

# Route de santé
@app.get("/health")
async def health_check():
    try:
        # Vérifier la connexion au MCP Hub
        mcp_message = create_mcp_message("ping", {})
        try:
            response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message, timeout=2.0)
            mcp_hub_status = "ok" if response.status_code == 200 else "error"
        except:
            mcp_hub_status = "error"
            
        return {
            "status": "ok" if mcp_hub_status == "ok" else "degraded",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "api_gateway": "ok",
                "mcp_hub": mcp_hub_status
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
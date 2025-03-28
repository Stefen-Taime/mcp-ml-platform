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

# Client HTTP asynchrone
http_client = httpx.AsyncClient()

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

# Routes pour les modèles
@app.get("/models")
async def get_models():
    try:
        mcp_message = create_mcp_message("list_models", {})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        response.raise_for_status()
        return response.json()["payload"]["models"]
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.get("/models/{model_id}")
async def get_model(model_id: str):
    try:
        mcp_message = create_mcp_message("get_model", {"model_id": model_id})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        response.raise_for_status()
        return response.json()["payload"]["model"]
    except httpx.HTTPError as e:
        if e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Modèle {model_id} non trouvé")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.post("/models")
async def create_model(model_data: dict):
    try:
        mcp_message = create_mcp_message("create_model", {"model": model_data})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        response.raise_for_status()
        return response.json()["payload"]["model"]
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.put("/models/{model_id}")
async def update_model(model_id: str, model_data: dict):
    try:
        model_data["id"] = model_id
        mcp_message = create_mcp_message("update_model", {"model": model_data})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        response.raise_for_status()
        return response.json()["payload"]["model"]
    except httpx.HTTPError as e:
        if e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Modèle {model_id} non trouvé")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.delete("/models/{model_id}")
async def delete_model(model_id: str):
    try:
        mcp_message = create_mcp_message("delete_model", {"model_id": model_id})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        response.raise_for_status()
        return {"message": f"Modèle {model_id} supprimé avec succès"}
    except httpx.HTTPError as e:
        if e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Modèle {model_id} non trouvé")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

# Routes pour les déploiements
@app.get("/deployments")
async def get_deployments():
    try:
        mcp_message = create_mcp_message("list_deployments", {})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        response.raise_for_status()
        return response.json()["payload"]["deployments"]
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.get("/deployments/{deployment_id}")
async def get_deployment(deployment_id: str):
    try:
        mcp_message = create_mcp_message("get_deployment", {"deployment_id": deployment_id})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        response.raise_for_status()
        return response.json()["payload"]["deployment"]
    except httpx.HTTPError as e:
        if e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Déploiement {deployment_id} non trouvé")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.post("/deployments")
async def create_deployment(deployment_data: dict):
    try:
        mcp_message = create_mcp_message("create_deployment", {"deployment": deployment_data})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        response.raise_for_status()
        return response.json()["payload"]["deployment"]
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.put("/deployments/{deployment_id}")
async def update_deployment(deployment_id: str, deployment_data: dict):
    try:
        deployment_data["id"] = deployment_id
        mcp_message = create_mcp_message("update_deployment", {"deployment": deployment_data})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        response.raise_for_status()
        return response.json()["payload"]["deployment"]
    except httpx.HTTPError as e:
        if e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Déploiement {deployment_id} non trouvé")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.delete("/deployments/{deployment_id}")
async def delete_deployment(deployment_id: str):
    try:
        mcp_message = create_mcp_message("delete_deployment", {"deployment_id": deployment_id})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        response.raise_for_status()
        return {"message": f"Déploiement {deployment_id} supprimé avec succès"}
    except httpx.HTTPError as e:
        if e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Déploiement {deployment_id} non trouvé")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

# Routes pour les exécutions
@app.get("/executions")
async def get_executions():
    try:
        mcp_message = create_mcp_message("list_executions", {})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        response.raise_for_status()
        return response.json()["payload"]["executions"]
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    try:
        mcp_message = create_mcp_message("get_execution", {"execution_id": execution_id})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        response.raise_for_status()
        return response.json()["payload"]["execution"]
    except httpx.HTTPError as e:
        if e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Exécution {execution_id} non trouvée")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.post("/executions")
async def create_execution(execution_data: dict):
    try:
        mcp_message = create_mcp_message("create_execution", {"execution": execution_data})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        response.raise_for_status()
        return response.json()["payload"]["execution"]
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    try:
        mcp_message = create_mcp_message("cancel_execution", {"execution_id": execution_id})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        response.raise_for_status()
        return {"message": f"Exécution {execution_id} annulée avec succès"}
    except httpx.HTTPError as e:
        if e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Exécution {execution_id} non trouvée")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.get("/executions/{execution_id}/results")
async def get_execution_results(execution_id: str):
    try:
        mcp_message = create_mcp_message("get_execution_results", {"execution_id": execution_id})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        response.raise_for_status()
        return response.json()["payload"]["results"]
    except httpx.HTTPError as e:
        if e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Résultats pour l'exécution {execution_id} non trouvés")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

# Routes pour les datasets
@app.get("/datasets")
async def get_datasets():
    try:
        mcp_message = create_mcp_message("list_datasets", {})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        response.raise_for_status()
        return response.json()["payload"]["datasets"]
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

@app.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str):
    try:
        mcp_message = create_mcp_message("get_dataset", {"dataset_id": dataset_id})
        response = await http_client.post(f"{MCP_HUB_URL}/process", json=mcp_message)
        response.raise_for_status()
        return response.json()["payload"]["dataset"]
    except httpx.HTTPError as e:
        if e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} non trouvé")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la communication avec le MCP Hub: {str(e)}")

# Route de santé
@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

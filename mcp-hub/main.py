import asyncio
import json
import uuid
from datetime import datetime
import os
import httpx
from typing import Dict, Any, List, Optional

# Configuration des URLs des services
MODEL_MCP_SERVER_URL = os.getenv("MODEL_MCP_SERVER_URL", "http://model-mcp-server:8002")
DATA_MCP_SERVER_URL = os.getenv("DATA_MCP_SERVER_URL", "http://data-mcp-server:8003")
EXECUTION_MCP_SERVER_URL = os.getenv("EXECUTION_MCP_SERVER_URL", "http://execution-mcp-server:8004")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://admin:adminpassword@mongodb:27017/mcpml?authSource=admin")

# Client HTTP asynchrone
http_client = httpx.AsyncClient(timeout=30.0)

# Classe principale du MCP Hub
class MCPHub:
    def __init__(self):
        self.server_urls = {
            "model-mcp-server": MODEL_MCP_SERVER_URL,
            "data-mcp-server": DATA_MCP_SERVER_URL,
            "execution-mcp-server": EXECUTION_MCP_SERVER_URL
        }
        
        # Mapping des opérations vers les serveurs
        self.operation_mapping = {
            # Opérations du Model MCP Server
            "list_models": "model-mcp-server",
            "get_model": "model-mcp-server",
            "create_model": "model-mcp-server",
            "update_model": "model-mcp-server",
            "delete_model": "model-mcp-server",
            "upload_model_file": "model-mcp-server",
            "download_model_file": "model-mcp-server",
            
            # Opérations du Data MCP Server
            "list_datasets": "data-mcp-server",
            "get_dataset": "data-mcp-server",
            "create_dataset": "data-mcp-server",
            "update_dataset": "data-mcp-server",
            "delete_dataset": "data-mcp-server",
            "upload_data": "data-mcp-server",
            "download_data": "data-mcp-server",
            "transform_data": "data-mcp-server",
            
            # Opérations de l'Execution MCP Server
            "list_deployments": "execution-mcp-server",
            "get_deployment": "execution-mcp-server",
            "create_deployment": "execution-mcp-server",
            "update_deployment": "execution-mcp-server",
            "delete_deployment": "execution-mcp-server",
            "list_executions": "execution-mcp-server",
            "get_execution": "execution-mcp-server",
            "create_execution": "execution-mcp-server",
            "cancel_execution": "execution-mcp-server",
            "get_execution_results": "execution-mcp-server",
            
            # Opérations complexes gérées par le MCP Hub
            "chain_operations": None,
            "validate_and_execute": None,
            "route_request": None,
            "parallel_execute": None,
            "orchestrate_task": None,
            "evaluate_and_optimize": None
        }
        
        print("MCP Hub initialized")
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite un message MCP et le route vers le serveur approprié
        """
        try:
            # Valider le message
            if not self._validate_message(message):
                return self._create_error_response(message, "Invalid MCP message format", 400)
            
            operation = message.get("operation")
            
            # Vérifier si l'opération est supportée
            if operation not in self.operation_mapping:
                return self._create_error_response(message, f"Unsupported operation: {operation}", 400)
            
            # Traiter les opérations complexes gérées par le MCP Hub
            if self.operation_mapping[operation] is None:
                if operation == "chain_operations":
                    return await self._handle_chain_operations(message)
                elif operation == "validate_and_execute":
                    return await self._handle_validate_and_execute(message)
                elif operation == "route_request":
                    return await self._handle_route_request(message)
                elif operation == "parallel_execute":
                    return await self._handle_parallel_execute(message)
                elif operation == "orchestrate_task":
                    return await self._handle_orchestrate_task(message)
                elif operation == "evaluate_and_optimize":
                    return await self._handle_evaluate_and_optimize(message)
            
            # Router le message vers le serveur approprié
            target_server = self.operation_mapping[operation]
            target_url = self.server_urls[target_server]
            
            # Modifier le destinataire du message
            message["recipient"] = {
                "id": target_server,
                "type": target_server
            }
            
            # Envoyer le message au serveur cible
            print(f"Routing operation '{operation}' to {target_server}")
            response = await http_client.post(f"{target_url}/process", json=message)
            
            # Vérifier la réponse
            if response.status_code != 200:
                return self._create_error_response(
                    message, 
                    f"Error from {target_server}: {response.text}", 
                    response.status_code
                )
            
            return response.json()
            
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            return self._create_error_response(message, f"Internal server error: {str(e)}", 500)
    
    def _validate_message(self, message: Dict[str, Any]) -> bool:
        """
        Valide le format d'un message MCP
        """
        required_fields = ["mcp_version", "message_id", "timestamp", "sender", "message_type", "operation"]
        return all(field in message for field in required_fields)
    
    def _create_error_response(self, request_message: Dict[str, Any], error_message: str, status_code: int) -> Dict[str, Any]:
        """
        Crée un message de réponse d'erreur
        """
        return {
            "mcp_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sender": {
                "id": "mcp-hub",
                "type": "mcp-hub"
            },
            "recipient": request_message.get("sender", {"id": "unknown", "type": "unknown"}),
            "message_type": "response",
            "operation": request_message.get("operation", "unknown"),
            "status": "error",
            "payload": {
                "error": error_message,
                "status_code": status_code
            },
            "metadata": {
                "request_id": request_message.get("message_id", "unknown")
            }
        }
    
    async def _handle_chain_operations(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gère le modèle d'agent de chaînage d'invites
        """
        operations = message.get("payload", {}).get("operations", [])
        if not operations:
            return self._create_error_response(message, "No operations provided for chaining", 400)
        
        result = None
        for i, operation in enumerate(operations):
            # Créer un nouveau message pour cette opération
            op_message = {
                "mcp_version": "1.0",
                "message_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "sender": message.get("sender"),
                "message_type": "request",
                "operation": operation.get("operation"),
                "payload": operation.get("payload", {})
            }
            
            # Si ce n'est pas la première opération, utiliser le résultat précédent
            if i > 0 and result:
                op_message["payload"]["previous_result"] = result.get("payload")
            
            # Traiter l'opération
            result = await self.process_message(op_message)
            
            # Si l'opération a échoué, arrêter la chaîne
            if result.get("status") == "error":
                return result
        
        # Créer une réponse finale
        return {
            "mcp_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sender": {
                "id": "mcp-hub",
                "type": "mcp-hub"
            },
            "recipient": message.get("sender"),
            "message_type": "response",
            "operation": "chain_operations",
            "status": "success",
            "payload": {
                "final_result": result.get("payload")
            },
            "metadata": {
                "request_id": message.get("message_id")
            }
        }
    
    async def _handle_validate_and_execute(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gère le modèle d'agent de portes (validation)
        """
        validation = message.get("payload", {}).get("validation", {})
        execution = message.get("payload", {}).get("execution", {})
        
        if not validation or not execution:
            return self._create_error_response(message, "Validation and execution details required", 400)
        
        # Vérifier les conditions
        conditions = validation.get("conditions", [])
        logic = validation.get("logic", "and")
        
        # Simuler la validation (dans un vrai système, cela vérifierait les conditions réelles)
        validation_passed = True
        
        # Si la validation échoue, renvoyer une erreur
        if not validation_passed:
            return self._create_error_response(message, "Validation failed", 422)
        
        # Si la validation réussit, exécuter l'opération
        exec_message = {
            "mcp_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sender": message.get("sender"),
            "message_type": "request",
            "operation": execution.get("operation"),
            "payload": execution.get("payload", {})
        }
        
        result = await self.process_message(exec_message)
        
        # Créer une réponse finale
        return {
            "mcp_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sender": {
                "id": "mcp-hub",
                "type": "mcp-hub"
            },
            "recipient": message.get("sender"),
            "message_type": "response",
            "operation": "validate_and_execute",
            "status": "success",
            "payload": {
                "validation": "passed",
                "execution_result": result.get("payload")
            },
            "metadata": {
                "request_id": message.get("message_id")
            }
        }
    
    async def _handle_route_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gère le modèle d'agent de routage
        """
        routing_rules = message.get("payload", {}).get("routing_rules", [])
        default_target = message.get("payload", {}).get("default_target")
        request = message.get("payload", {}).get("request", {})
        
        if not routing_rules or not default_target or not request:
            return self._create_error_response(message, "Routing rules, default target, and request required", 400)
        
        # Déterminer la cible en fonction des règles (simulé ici)
        target = default_target
        
        # Créer un message pour la requête routée
        routed_message = {
            "mcp_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sender": message.get("sender"),
            "recipient": target,
            "message_type": "request",
            "operation": request.get("operation"),
            "payload": request.get("payload", {})
        }
        
        # Traiter le message routé
        result = await self.process_message(routed_message)
        
        # Créer une réponse finale
        return {
            "mcp_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sender": {
                "id": "mcp-hub",
                "type": "mcp-hub"
            },
            "recipient": message.get("sender"),
            "message_type": "response",
            "operation": "route_request",
            "status": "success",
            "payload": {
                "routed_to": target,
                "result": result.get("payload")
            },
            "metadata": {
                "request_id": message.get("message_id")
            }
        }
    
    async def _handle_parallel_execute(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gère le modèle d'agent de parallélisation
        """
        executions = message.get("payload", {}).get("executions", [])
        aggregation = message.get("payload", {}).get("aggregation", {})
        
        if not executions:
            return self._create_error_response(message, "No executions provided for parallel processing", 400)
        
        # Créer des messages pour chaque exécution
        execution_messages = []
        for execution in executions:
            exec_message = {
                "mcp_version": "1.0",
                "message_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "sender": message.get("sender"),
                "message_type": "request",
                "operation": execution.get("operation"),
                "payload": execution.get("payload", {})
            }
            execution_messages.append(exec_message)
        
        # Exécuter les messages en parallèle
        tasks = [self.process_message(msg) for msg in execution_messages]
        results = await asyncio.gather(*tasks)
        
        # Agréger les résultats (simulé ici)
        aggregated_result = {
            "results": [result.get("payload") for result in results]
        }
        
        # Créer une réponse finale
        return {
            "mcp_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sender": {
                "id": "mcp-hub",
                "type": "mcp-hub"
            },
            "recipient": message.get("sender"),
            "message_type": "response",
            "operation": "parallel_execute",
            "status": "success",
            "payload": aggregated_result,
            "metadata": {
                "request_id": message.get("message_id")
            }
        }
    
    async def _handle_orchestrate_task(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gère le modèle d'agent d'orchestrateurs-ouvriers
        """
        task_id = message.get("payload", {}).get("task_id")
        workers = message.get("payload", {}).get("workers", [])
        workflow = message.get("payload", {}).get("workflow", [])
        
        if not task_id or not workers or not workflow:
            return self._create_error_response(message, "Task ID, workers, and workflow required", 400)
        
        # Exécuter les étapes du workflow séquentiellement
        step_results = {}
        for step in sorted(workflow, key=lambda x: x.get("step", 0)):
            step_num = step.get("step")
            worker_role = step.get("worker_role")
            operation = step.get("operation")
            payload = step.get("payload", {})
            
            # Trouver le worker pour ce rôle
            worker = next((w for w in workers if w.get("role") == worker_role), None)
            if not worker:
                return self._create_error_response(message, f"No worker found for role: {worker_role}", 400)
            
            # Créer un message pour cette étape
            step_message = {
                "mcp_version": "1.0",
                "message_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "sender": message.get("sender"),
                "message_type": "request",
                "operation": operation,
                "payload": {
                    **payload,
                    "worker": worker,
                    "task_id": task_id,
                    "step": step_num,
                    "previous_steps": step_results
                }
            }
            
            # Traiter l'étape
            result = await self.process_message(step_message)
            
            # Si l'étape a échoué, arrêter le workflow
            if result.get("status") == "error":
                return self._create_error_response(
                    message, 
                    f"Step {step_num} failed: {result.get('payload', {}).get('error')}", 
                    500
                )
            
            # Stocker le résultat de cette étape
            step_results[str(step_num)] = result.get("payload")
        
        # Créer une réponse finale
        return {
            "mcp_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sender": {
                "id": "mcp-hub",
                "type": "mcp-hub"
            },
            "recipient": message.get("sender"),
            "message_type": "response",
            "operation": "orchestrate_task",
            "status": "success",
            "payload": {
                "task_id": task_id,
                "workflow_completed": True,
                "step_results": step_results,
                "final_result": step_results.get(str(max(int(k) for k in step_results.keys())))
            },
            "metadata": {
                "request_id": message.get("message_id")
            }
        }
    
    async def _handle_evaluate_and_optimize(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gère le modèle d'agent d'évaluation et d'optimisation
        """
        model_id = message.get("payload", {}).get("model_id")
        dataset_id = message.get("payload", {}).get("dataset_id")
        metrics = message.get("payload", {}).get("metrics", [])
        optimization_params = message.get("payload", {}).get("optimization_params", {})
        
        if not model_id or not dataset_id or not metrics:
            return self._create_error_response(message, "Model ID, dataset ID, and metrics required", 400)
        
        # 1. Récupérer le modèle
        model_message = {
            "mcp_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sender": message.get("sender"),
            "message_type": "request",
            "operation": "get_model",
            "payload": {"model_id": model_id}
        }
        
        model_result = await self.process_message(model_message)
        if model_result.get("status") == "error":
            return model_result
        
        # 2. Récupérer le dataset
        dataset_message = {
            "mcp_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sender": message.get("sender"),
            "message_type": "request",
            "operation": "get_dataset",
            "payload": {"dataset_id": dataset_id}
        }
        
        dataset_result = await self.process_message(dataset_message)
        if dataset_result.get("status") == "error":
            return dataset_result
        
        # 3. Créer un déploiement de test
        deployment_message = {
            "mcp_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sender": message.get("sender"),
            "message_type": "request",
            "operation": "create_deployment",
            "payload": {
                "deployment": {
                    "name": f"Evaluation-{model_id[:8]}",
                    "description": f"Temporary deployment for model evaluation",
                    "model_id": model_id,
                    "model_name": model_result.get("payload", {}).get("model", {}).get("name", "Unknown Model"),
                    "environment": "evaluation",
                    "status": "active"
                }
            }
        }
        
        deployment_result = await self.process_message(deployment_message)
        if deployment_result.get("status") == "error":
            return deployment_result
        
        deployment_id = deployment_result.get("payload", {}).get("deployment", {}).get("id")
        
        # 4. Exécuter l'évaluation
        execution_message = {
            "mcp_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sender": message.get("sender"),
            "message_type": "request",
            "operation": "create_execution",
            "payload": {
                "execution": {
                    "deployment_id": deployment_id,
                    "dataset_id": dataset_id,
                    "parameters": {
                        "metrics": metrics,
                        "optimization_params": optimization_params
                    }
                }
            }
        }
        
        execution_result = await self.process_message(execution_message)
        if execution_result.get("status") == "error":
            # Nettoyer le déploiement temporaire
            await self._cleanup_deployment(deployment_id)
            return execution_result
        
        execution_id = execution_result.get("payload", {}).get("execution", {}).get("id")
        
        # 5. Récupérer les résultats
        results_message = {
            "mcp_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sender": message.get("sender"),
            "message_type": "request",
            "operation": "get_execution_results",
            "payload": {"execution_id": execution_id}
        }
        
        results = await self.process_message(results_message)
        
        # 6. Nettoyer le déploiement temporaire
        await self._cleanup_deployment(deployment_id)
        
        # Créer la réponse finale avec les résultats d'évaluation
        return {
            "mcp_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "sender": {
                "id": "mcp-hub",
                "type": "mcp-hub"
            },
            "recipient": message.get("sender"),
            "message_type": "response",
            "operation": "evaluate_and_optimize",
            "status": "success",
            "payload": {
                "model_id": model_id,
                "dataset_id": dataset_id,
                "evaluation_results": results.get("payload", {}).get("results", {}),
                "optimization_suggestions": {
                    "suggested_params": {
                        "learning_rate": 0.001,
                        "batch_size": 64,
                        "epochs": 10
                    },
                    "estimated_improvement": "+5.2%"
                }
            },
            "metadata": {
                "request_id": message.get("message_id")
            }
        }
    
    async def _cleanup_deployment(self, deployment_id: str):
        """
        Nettoie un déploiement temporaire
        """
        try:
            cleanup_message = {
                "mcp_version": "1.0",
                "message_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "sender": {
                    "id": "mcp-hub",
                    "type": "mcp-hub"
                },
                "message_type": "request",
                "operation": "delete_deployment",
                "payload": {"deployment_id": deployment_id}
            }
            
            await self.process_message(cleanup_message)
        except Exception as e:
            print(f"Error cleaning up deployment {deployment_id}: {str(e)}")

# Point d'entrée FastAPI
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="MCP Hub")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Pour le développement, à restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instance du MCP Hub
mcp_hub = MCPHub()

@app.post("/process")
async def process_message(request: Request):
    """
    Point d'entrée pour traiter un message MCP
    """
    try:
        message = await request.json()
        response = await mcp_hub.process_message(message)
        return JSONResponse(content=response)
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "mcp_version": "1.0",
                "message_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "sender": {
                    "id": "mcp-hub",
                    "type": "mcp-hub"
                },
                "message_type": "response",
                "status": "error",
                "payload": {
                    "error": f"Internal server error: {str(e)}",
                    "status_code": 500
                }
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
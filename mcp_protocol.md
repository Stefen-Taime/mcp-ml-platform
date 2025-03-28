# Protocole MCP (Model Context Protocol)

## Introduction

Le protocole MCP est un standard de communication conçu pour faciliter les interactions entre les différents composants d'une plateforme de modèles d'apprentissage automatique. Il définit un format commun pour les requêtes et les réponses, permettant une interopérabilité transparente entre les services.

## Structure de base d'un message MCP

Tous les messages MCP suivent une structure JSON commune :

```json
{
  "mcp_version": "1.0",
  "message_id": "uuid-string",
  "timestamp": "iso-datetime-string",
  "sender": {
    "id": "sender-service-id",
    "type": "service-type"
  },
  "recipient": {
    "id": "recipient-service-id",
    "type": "service-type"
  },
  "message_type": "request|response|event",
  "operation": "operation-name",
  "status": "success|error|pending",
  "payload": {},
  "metadata": {}
}
```

## Types de messages

### Request

Un message de requête est envoyé pour demander une action ou des informations.

```json
{
  "mcp_version": "1.0",
  "message_id": "req-123",
  "timestamp": "2025-03-28T17:45:00Z",
  "sender": {
    "id": "api-gateway-1",
    "type": "api-gateway"
  },
  "recipient": {
    "id": "model-server-1",
    "type": "model-mcp-server"
  },
  "message_type": "request",
  "operation": "get_model",
  "payload": {
    "model_id": "model-123"
  },
  "metadata": {
    "priority": "high",
    "timeout": 30
  }
}
```

### Response

Un message de réponse est renvoyé suite à une requête.

```json
{
  "mcp_version": "1.0",
  "message_id": "resp-456",
  "timestamp": "2025-03-28T17:45:05Z",
  "sender": {
    "id": "model-server-1",
    "type": "model-mcp-server"
  },
  "recipient": {
    "id": "api-gateway-1",
    "type": "api-gateway"
  },
  "message_type": "response",
  "operation": "get_model",
  "status": "success",
  "payload": {
    "model_id": "model-123",
    "name": "Sales Prediction Model",
    "version": "1.0",
    "framework": "scikit-learn",
    "created_at": "2025-03-20T10:00:00Z"
  },
  "metadata": {
    "request_id": "req-123",
    "processing_time": 0.05
  }
}
```

### Event

Un message d'événement est émis pour notifier d'un changement d'état ou d'une action asynchrone.

```json
{
  "mcp_version": "1.0",
  "message_id": "evt-789",
  "timestamp": "2025-03-28T17:46:00Z",
  "sender": {
    "id": "execution-server-1",
    "type": "execution-mcp-server"
  },
  "recipient": {
    "id": "mcp-hub",
    "type": "mcp-hub"
  },
  "message_type": "event",
  "operation": "execution_completed",
  "status": "success",
  "payload": {
    "execution_id": "exec-123",
    "model_id": "model-123",
    "duration": 120,
    "result_location": "minio://results/exec-123/"
  },
  "metadata": {
    "deployment_id": "deploy-456"
  }
}
```

## Opérations standard par type de serveur

### Model MCP Server

- `list_models`: Liste tous les modèles disponibles
- `get_model`: Récupère les détails d'un modèle spécifique
- `create_model`: Crée un nouveau modèle
- `update_model`: Met à jour un modèle existant
- `delete_model`: Supprime un modèle
- `upload_model_file`: Télécharge un fichier de modèle
- `download_model_file`: Télécharge un fichier de modèle

### Data MCP Server

- `list_datasets`: Liste tous les ensembles de données disponibles
- `get_dataset`: Récupère les détails d'un ensemble de données spécifique
- `create_dataset`: Crée un nouvel ensemble de données
- `update_dataset`: Met à jour un ensemble de données existant
- `delete_dataset`: Supprime un ensemble de données
- `upload_data`: Télécharge des données
- `download_data`: Télécharge des données
- `transform_data`: Transforme des données selon des règles spécifiées

### Execution MCP Server

- `list_deployments`: Liste tous les déploiements
- `get_deployment`: Récupère les détails d'un déploiement spécifique
- `create_deployment`: Crée un nouveau déploiement
- `update_deployment`: Met à jour un déploiement existant
- `delete_deployment`: Supprime un déploiement
- `list_executions`: Liste toutes les exécutions
- `get_execution`: Récupère les détails d'une exécution spécifique
- `create_execution`: Crée une nouvelle exécution
- `cancel_execution`: Annule une exécution en cours
- `get_execution_results`: Récupère les résultats d'une exécution

## Modèles d'agents implémentés via MCP

### Chaînage d'invites

Permet d'enchaîner plusieurs opérations séquentiellement, chaque opération utilisant le résultat de la précédente.

```json
{
  "operation": "chain_operations",
  "payload": {
    "operations": [
      {
        "operation": "transform_data",
        "payload": { "dataset_id": "dataset-123", "transformations": [...] }
      },
      {
        "operation": "create_execution",
        "payload": { "model_id": "model-123", "deployment_id": "deploy-456" }
      },
      {
        "operation": "get_execution_results",
        "payload": { "format": "json" }
      }
    ]
  }
}
```

### Portes (validation)

Vérifie des conditions avant de poursuivre l'exécution.

```json
{
  "operation": "validate_and_execute",
  "payload": {
    "validation": {
      "conditions": [
        { "field": "model.status", "operator": "equals", "value": "active" },
        { "field": "user.permissions", "operator": "contains", "value": "execute_model" }
      ],
      "logic": "and"
    },
    "execution": {
      "operation": "create_execution",
      "payload": { "model_id": "model-123", "parameters": {...} }
    }
  }
}
```

### Routage

Dirige les requêtes vers différents services en fonction de critères spécifiques.

```json
{
  "operation": "route_request",
  "payload": {
    "routing_rules": [
      {
        "condition": { "field": "model.framework", "operator": "equals", "value": "tensorflow" },
        "target": { "id": "execution-server-tf", "type": "execution-mcp-server" }
      },
      {
        "condition": { "field": "model.framework", "operator": "equals", "value": "pytorch" },
        "target": { "id": "execution-server-pt", "type": "execution-mcp-server" }
      }
    ],
    "default_target": { "id": "execution-server-default", "type": "execution-mcp-server" },
    "request": {
      "operation": "create_execution",
      "payload": { "model_id": "model-123", "parameters": {...} }
    }
  }
}
```

### Parallélisation (sectionnement et vote)

Exécute plusieurs opérations en parallèle et agrège les résultats.

```json
{
  "operation": "parallel_execute",
  "payload": {
    "executions": [
      {
        "operation": "create_execution",
        "payload": { "model_id": "model-123", "parameters": { "region": "europe" } }
      },
      {
        "operation": "create_execution",
        "payload": { "model_id": "model-123", "parameters": { "region": "americas" } }
      },
      {
        "operation": "create_execution",
        "payload": { "model_id": "model-123", "parameters": { "region": "asia" } }
      }
    ],
    "aggregation": {
      "type": "average",
      "fields": ["prediction.sales", "prediction.revenue"]
    }
  }
}
```

### Orchestrateurs-Ouvriers

Distribue des tâches à plusieurs services et coordonne leur exécution.

```json
{
  "operation": "orchestrate_task",
  "payload": {
    "task_id": "task-123",
    "workers": [
      { "id": "data-server-1", "type": "data-mcp-server", "role": "data_preparation" },
      { "id": "model-server-1", "type": "model-mcp-server", "role": "model_retrieval" },
      { "id": "execution-server-1", "type": "execution-mcp-server", "role": "model_execution" }
    ],
    "workflow": [
      {
        "step": 1,
        "worker_role": "data_preparation",
        "operation": "transform_data",
        "payload": { "dataset_id": "dataset-123" }
      },
      {
        "step": 2,
        "worker_role": "model_retrieval",
        "operation": "get_model",
        "payload": { "model_id": "model-123" }
      },
      {
        "step": 3,
        "worker_role": "model_execution",
        "operation": "create_execution",
        "payload": { "use_results_from_step": 1, "use_model_from_step": 2 }
      }
    ]
  }
}
```

### Évaluateur-Optimiseur

Évalue les performances d'un modèle et optimise ses paramètres.

```json
{
  "operation": "evaluate_and_optimize",
  "payload": {
    "model_id": "model-123",
    "evaluation": {
      "metrics": ["accuracy", "precision", "recall", "f1_score"],
      "dataset_id": "validation-dataset-456"
    },
    "optimization": {
      "parameters": [
        { "name": "learning_rate", "range": [0.001, 0.1], "type": "float", "scale": "log" },
        { "name": "batch_size", "values": [16, 32, 64, 128], "type": "int" }
      ],
      "objective": "maximize",
      "metric": "f1_score",
      "max_iterations": 20,
      "algorithm": "bayesian"
    }
  }
}
```

## Codes d'erreur

- `400`: Requête invalide
- `401`: Non autorisé
- `403`: Accès refusé
- `404`: Ressource non trouvée
- `409`: Conflit
- `422`: Entité non traitable
- `500`: Erreur interne du serveur
- `503`: Service indisponible
- `504`: Délai d'attente dépassé

## Sécurité

Tous les messages MCP doivent être transmis via HTTPS. L'authentification est gérée via des jetons JWT inclus dans l'en-tête HTTP ou dans le champ `metadata.auth_token` du message MCP.

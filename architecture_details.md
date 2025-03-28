# Architecture de la Plateforme Centralisée de Modèles ML

## Vue d'ensemble

Cette plateforme centralisée de modèles ML utilise une approche API-First avec le protocole MCP (Model Context Protocol) pour standardiser les communications entre les différents composants. L'architecture est conçue pour être modulaire, évolutive et facilement extensible.

## Composants principaux

### 1. Frontend (Next.js)

Le frontend est développé avec Next.js et Tailwind CSS, offrant une interface utilisateur moderne et réactive. Il comprend les pages suivantes :
- Dashboard : Vue d'ensemble de la plateforme
- Modèles : Gestion des modèles ML
- Déploiements : Gestion des déploiements de modèles
- Exécutions : Suivi et gestion des exécutions de modèles
- Datasets : Gestion des ensembles de données

Le frontend communique exclusivement avec l'API Gateway via des appels HTTP RESTful.

### 2. API Gateway (FastAPI)

L'API Gateway sert de point d'entrée unique pour toutes les requêtes. Développé avec FastAPI, il offre :
- Routage des requêtes vers les services appropriés
- Validation des requêtes
- Journalisation des requêtes
- Gestion des erreurs

L'API Gateway traduit les requêtes HTTP en messages MCP et les envoie au MCP Hub.

### 3. MCP Hub

Le MCP Hub est le cœur de l'architecture, responsable de :
- Coordonner les communications entre les serveurs MCP spécialisés
- Router les messages MCP vers les serveurs appropriés
- Implémenter les modèles d'agents (chaînage, portes, routage, etc.)
- Orchestrer les flux de travail complexes

### 4. Serveurs MCP spécialisés

#### Model MCP Server
- Gestion des modèles ML (CRUD)
- Stockage et récupération des fichiers de modèles via MinIO
- Gestion des métadonnées des modèles dans MongoDB

#### Data MCP Server
- Gestion des datasets (CRUD)
- Stockage et récupération des données via MinIO
- Transformation des données
- Gestion des métadonnées des datasets dans MongoDB

#### Execution MCP Server
- Gestion des déploiements de modèles
- Exécution des modèles via Groq pour l'inférence
- Traitement distribué via Spark
- Stockage des résultats d'exécution dans MinIO
- Gestion des métadonnées des exécutions dans MongoDB

### 5. Services de stockage et bases de données

#### MinIO
- Stockage d'objets compatible S3
- Buckets pour les modèles, datasets et résultats
- Gestion des accès et des politiques

#### MongoDB
- Stockage des métadonnées pour tous les composants
- Collections pour les modèles, datasets, déploiements et exécutions
- Indexation pour des performances optimales

### 6. Services de traitement

#### Spark
- Traitement distribué des données
- Exécution des modèles ML à grande échelle
- Intégration avec MinIO pour l'accès aux données

### 7. Nginx

- Routage des requêtes vers les différents services
- Point d'entrée unique pour l'ensemble de la plateforme
- Configuration des chemins d'accès pour chaque service

## Protocole MCP (Model Context Protocol)

Le protocole MCP est un protocole de communication standardisé utilisé par tous les composants de la plateforme. Chaque message MCP contient :

```json
{
  "mcp_version": "1.0",
  "message_id": "uuid-string",
  "timestamp": "iso-datetime",
  "sender": {
    "id": "sender-id",
    "type": "sender-type"
  },
  "recipient": {
    "id": "recipient-id",
    "type": "recipient-type"
  },
  "message_type": "request|response",
  "operation": "operation-name",
  "payload": {},
  "metadata": {}
}
```

## Modèles d'agents

La plateforme implémente plusieurs modèles d'agents pour gérer différents cas d'utilisation :

### 1. Chaînage d'invites
- Exécution séquentielle d'opérations
- Passage des résultats d'une opération à la suivante

### 2. Portes (Validation)
- Validation des conditions avant exécution
- Contrôle d'accès et vérification des prérequis

### 3. Routage
- Direction des requêtes vers différents services
- Sélection dynamique des destinataires

### 4. Parallélisation
- Exécution parallèle de plusieurs opérations
- Agrégation des résultats

### 5. Orchestrateurs-Ouvriers
- Distribution des tâches entre plusieurs travailleurs
- Coordination et suivi de l'avancement

### 6. Évaluateur-Optimiseur
- Évaluation des performances des modèles
- Optimisation des hyperparamètres

## Flux de données

1. L'utilisateur interagit avec le frontend
2. Le frontend envoie des requêtes à l'API Gateway
3. L'API Gateway traduit les requêtes en messages MCP et les envoie au MCP Hub
4. Le MCP Hub route les messages vers les serveurs MCP appropriés
5. Les serveurs MCP traitent les messages et interagissent avec les services de stockage et de traitement
6. Les résultats remontent par le même chemin jusqu'au frontend

## Déploiement

La plateforme est déployée à l'aide de Docker Compose, avec un conteneur pour chaque composant :
- frontend
- api-gateway
- mcp-hub
- model-mcp-server
- data-mcp-server
- execution-mcp-server
- mongodb
- mongo-express
- minio
- spark-master
- spark-worker
- nginx

## Sécurité

Dans ce POC, la sécurité est minimale. Pour une version de production, il faudrait ajouter :
- Authentification et autorisation (Keycloak)
- Chiffrement des communications (HTTPS)
- Gestion des secrets (Vault)
- Audit et journalisation

## Évolutivité

L'architecture est conçue pour être évolutive :
- Ajout de nouveaux serveurs MCP spécialisés
- Mise à l'échelle horizontale des composants existants
- Intégration avec d'autres services et outils

## Diagramme d'architecture

```
+----------------+     +----------------+     +----------------+
|                |     |                |     |                |
|    Frontend    |---->|  API Gateway   |---->|    MCP Hub     |
|    (Next.js)   |<----|    (FastAPI)   |<----|                |
|                |     |                |     |                |
+----------------+     +----------------+     +-------+--------+
                                                     |
                                                     |
                       +---------------------------+-+-------------------------+
                       |                           |                           |
                       v                           v                           v
              +----------------+          +----------------+          +----------------+
              |                |          |                |          |                |
              | Model MCP      |          | Data MCP       |          | Execution MCP  |
              | Server         |          | Server         |          | Server         |
              |                |          |                |          |                |
              +-------+--------+          +-------+--------+          +-------+--------+
                      |                           |                           |
                      |                           |                           |
              +-------v--------+          +-------v--------+          +-------v--------+
              |                |          |                |          |                |
              |     MinIO      |          |    MongoDB     |          |     Spark      |
              |                |          |                |          |                |
              +----------------+          +----------------+          +----------------+
```

## Conclusion

Cette architecture API-First avec le protocole MCP offre une solution robuste, flexible et évolutive pour la gestion centralisée des modèles ML. La standardisation des communications et la modularité des composants permettent une maintenance facile et une extension future de la plateforme.

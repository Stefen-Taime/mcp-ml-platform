# Architecture de la Plateforme Centralisée de Modèles ML

## Vue d'ensemble

La plateforme centralisée de modèles ML est conçue selon une approche API-First avec le protocole MCP (Model Context Protocol) pour standardiser les communications entre les différents composants. L'architecture est déployée via Docker Compose pour faciliter le développement, les tests et le déploiement.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                  NGINX                                   │
│                           (Proxy Inverse)                                │
└───────────┬─────────────────┬──────────────────┬──────────────────┬─────┘
            │                 │                  │                  │
            ▼                 ▼                  ▼                  ▼
┌────────────────┐  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐
│    Frontend    │  │ API Gateway  │  │ Mongo Express │  │  MinIO Console   │
│    (Next.js)   │  │  (FastAPI)   │  │              │  │                   │
└────────┬───────┘  └───────┬──────┘  └───────┬───────┘  └─────────┬────────┘
         │                  │                 │                    │
         │                  ▼                 │                    │
         │         ┌──────────────┐           │                    │
         │         │   MCP Hub    │           │                    │
         │         │              │           │                    │
         │         └──┬─────┬─────┘           │                    │
         │            │     │                 │                    │
         │            ▼     ▼                 │                    │
┌────────▼────────┐  ┌─────▼─────┐  ┌─────────▼─────────┐  ┌──────▼───────┐
│  Model MCP      │  │ Data MCP  │  │  Execution MCP    │  │               │
│  Server         │  │ Server    │  │  Server           │  │     MinIO     │
│  (FastAPI)      │  │ (FastAPI) │  │  (FastAPI)        │  │               │
└────────┬────────┘  └─────┬─────┘  └─────────┬─────────┘  └──────┬───────┘
         │                 │                  │                   │
         │                 │                  ▼                   │
         │                 │         ┌────────────────┐           │
         │                 │         │  Spark Master  │           │
         │                 │         │                │           │
         │                 │         └────────┬───────┘           │
         │                 │                  │                   │
         │                 │                  ▼                   │
         │                 │         ┌────────────────┐           │
         │                 │         │  Spark Worker  │           │
         │                 │         │                │           │
         │                 │         └────────────────┘           │
         │                 │                                      │
         ▼                 ▼                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                                MongoDB                                   │
│                          (Base de données)                               │
└─────────────────────────────────────────────────────────────────────────┘
```

## Composants principaux

### 1. Frontend (Next.js)

Interface utilisateur permettant aux utilisateurs d'interagir avec la plateforme. Principales fonctionnalités :
- Tableau de bord
- Gestion des modèles (liste, détail, création)
- Gestion des déploiements (liste, détail, création)
- Suivi des exécutions (liste, détail)
- Gestion des utilisateurs

### 2. API Gateway (FastAPI)

Point d'entrée unique pour toutes les requêtes API. Responsabilités :
- Routage des requêtes vers les services appropriés
- Validation des requêtes
- Authentification et autorisation
- Gestion des erreurs
- Documentation de l'API (via Swagger UI)

### 3. MCP Hub

Coordonnateur central pour tous les serveurs MCP. Responsabilités :
- Gestion des communications entre les serveurs MCP
- Orchestration des workflows
- Implémentation des modèles d'agents (chaînage, portes, routage, etc.)
- Suivi de l'état des serveurs MCP

### 4. Serveurs MCP spécialisés

#### 4.1. Model MCP Server

Gestion des modèles ML. Responsabilités :
- CRUD des modèles
- Stockage et récupération des fichiers de modèles via MinIO
- Gestion des versions des modèles
- Métadonnées des modèles dans MongoDB

#### 4.2. Data MCP Server

Gestion des données. Responsabilités :
- CRUD des ensembles de données
- Stockage et récupération des données via MinIO
- Transformation des données
- Métadonnées des ensembles de données dans MongoDB

#### 4.3. Execution MCP Server

Exécution des modèles. Responsabilités :
- Gestion des déploiements
- Exécution des modèles via Groq
- Traitement distribué via Spark
- Stockage des résultats dans MinIO
- Métadonnées des exécutions dans MongoDB

### 5. Services de stockage et bases de données

#### 5.1. MongoDB

Base de données pour les métadonnées. Stocke :
- Informations sur les modèles
- Informations sur les ensembles de données
- Informations sur les déploiements
- Informations sur les exécutions
- Informations sur les utilisateurs

#### 5.2. MinIO

Stockage d'objets pour :
- Fichiers de modèles
- Ensembles de données
- Résultats d'exécution
- Fichiers de configuration

#### 5.3. Mongo Express

Interface web pour la gestion de MongoDB.

### 6. Services de traitement

#### 6.1. Spark Master

Coordinateur pour le traitement distribué.

#### 6.2. Spark Worker

Nœud de travail pour le traitement distribué.

### 7. Nginx

Proxy inverse pour :
- Router le trafic vers le frontend sur /
- Router le trafic API vers l'API gateway sur /api
- Exposer les services de gestion (Minio Console, Mongo Express) sur des sous-chemins sécurisés

## Flux de données

1. L'utilisateur interagit avec le frontend
2. Le frontend envoie des requêtes à l'API Gateway
3. L'API Gateway route les requêtes vers le MCP Hub
4. Le MCP Hub coordonne les communications entre les serveurs MCP
5. Les serveurs MCP interagissent avec MongoDB pour les métadonnées et MinIO pour le stockage d'objets
6. L'Execution MCP Server utilise Groq pour l'inférence et Spark pour le traitement distribué
7. Les résultats sont stockés dans MinIO et les métadonnées dans MongoDB
8. Le frontend récupère et affiche les résultats à l'utilisateur

## Modèles d'agents implémentés

1. **Chaînage d'invites** : Enchaînement séquentiel d'opérations
2. **Portes (validation)** : Vérification de conditions avant exécution
3. **Routage** : Direction des requêtes vers différents services
4. **Parallélisation (sectionnement et vote)** : Exécution parallèle et agrégation
5. **Orchestrateurs-Ouvriers** : Distribution et coordination de tâches
6. **Évaluateur-Optimiseur** : Évaluation et optimisation des performances

## Communication via MCP

Tous les composants communiquent via le protocole MCP, qui définit un format standard pour les requêtes et les réponses. Voir le fichier `mcp_protocol.md` pour plus de détails.

## Déploiement

L'ensemble de la plateforme est déployé via Docker Compose, avec un conteneur Docker pour chaque service. Chaque service personnalisé (frontend, api-gateway, mcp-hub, et les serveurs MCP) a son propre Dockerfile dans son répertoire respectif.

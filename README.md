# Guide d'utilisation - Plateforme Centralisée de Modèles ML

## Introduction

Ce document présente un guide d'utilisation complet pour la plateforme centralisée de modèles ML développée avec l'approche API-First et le protocole MCP (Model Context Protocol). Cette plateforme permet de centraliser, déployer et exécuter des modèles d'apprentissage automatique de manière standardisée et évolutive.

## Architecture de la plateforme

La plateforme est composée des éléments suivants :

1. **Frontend (Next.js)** : Interface utilisateur pour interagir avec la plateforme
2. **API Gateway (FastAPI)** : Point d'entrée unique pour toutes les requêtes
3. **MCP Hub** : Coordinateur central qui gère les communications entre les serveurs MCP
4. **Serveurs MCP spécialisés** :
   - **Model MCP Server** : Gestion des modèles ML
   - **Data MCP Server** : Accès aux données
   - **Execution MCP Server** : Exécution des modèles via Groq et Spark
5. **Services de stockage et bases de données** :
   - **MinIO** : Stockage des modèles, datasets et résultats
   - **MongoDB** : Stockage des métadonnées
6. **Services de traitement** :
   - **Spark** : Traitement distribué des données

## Prérequis

- Docker et Docker Compose
- Clé API Groq (pour l'inférence des modèles)

## Installation et démarrage

1. Clonez le dépôt :
   ```bash
   git clone <repository-url>
   cd mcp-ml-platform
   ```

2. Configurez les variables d'environnement dans le fichier `.env` :
   ```
   MONGO_INITDB_ROOT_USERNAME=admin
   MONGO_INITDB_ROOT_PASSWORD=adminpassword
   MINIO_ROOT_USER=minioadmin
   MINIO_ROOT_PASSWORD=minioadmin
   GROQ_API_KEY=votre-clé-api-groq
   ```

3. Démarrez la plateforme :
   ```bash
   docker-compose up -d
   ```

4. Accédez à l'interface utilisateur :
   ```
   http://localhost
   ```

## Utilisation de la plateforme

### 1. Gestion des modèles

#### Ajouter un nouveau modèle

1. Accédez à la page "Modèles" et cliquez sur "Ajouter un modèle"
2. Remplissez les informations du modèle :
   - Nom
   - Description
   - Type (classification, régression, etc.)
   - Framework (PyTorch, TensorFlow, etc.)
3. Téléchargez le fichier du modèle
4. Cliquez sur "Créer"

#### Consulter les détails d'un modèle

1. Accédez à la page "Modèles"
2. Cliquez sur le modèle souhaité pour voir ses détails

### 2. Gestion des datasets

#### Ajouter un nouveau dataset

1. Accédez à la page "Datasets" et cliquez sur "Ajouter un dataset"
2. Remplissez les informations du dataset :
   - Nom
   - Description
   - Type (image, texte, tabulaire, etc.)
3. Téléchargez le fichier du dataset
4. Cliquez sur "Créer"

### 3. Déploiement de modèles

#### Créer un déploiement

1. Accédez à la page "Déploiements" et cliquez sur "Créer un déploiement"
2. Sélectionnez le modèle à déployer
3. Configurez les paramètres du déploiement :
   - Nom du déploiement
   - Environnement (production, staging, etc.)
   - Ressources allouées
4. Cliquez sur "Déployer"

### 4. Exécution de modèles

#### Lancer une exécution

1. Accédez à la page "Exécutions" et cliquez sur "Nouvelle exécution"
2. Sélectionnez le déploiement à utiliser
3. Configurez les paramètres d'exécution :
   - Dataset à utiliser
   - Paramètres spécifiques au modèle
4. Cliquez sur "Exécuter"

#### Consulter les résultats d'une exécution

1. Accédez à la page "Exécutions"
2. Cliquez sur l'exécution souhaitée pour voir ses détails et résultats
3. Visualisez les métriques et téléchargez les résultats

## Administration de la plateforme

### Accès aux interfaces d'administration

- **MinIO Console** : http://localhost/minio/
- **Mongo Express** : http://localhost/mongo-express/
- **Spark UI** : http://localhost/spark/

### Gestion des utilisateurs

La gestion des utilisateurs n'est pas implémentée dans ce POC, mais pourrait être ajoutée en intégrant un service d'authentification comme Keycloak.

## Protocole MCP (Model Context Protocol)

Le protocole MCP est au cœur de la plateforme et standardise les communications entre les différents composants. Chaque message MCP contient :

- Version du protocole
- ID du message
- Horodatage
- Expéditeur et destinataire
- Type de message (requête/réponse)
- Opération à effectuer
- Charge utile (payload)
- Métadonnées

## Modèles d'agents implémentés

La plateforme implémente plusieurs modèles d'agents pour gérer différents cas d'utilisation :

1. **Chaînage d'invites** : Exécution séquentielle d'opérations
2. **Portes** : Validation avant exécution
3. **Routage** : Direction des requêtes vers différents services
4. **Parallélisation** : Exécution parallèle et agrégation
5. **Orchestrateurs-Ouvriers** : Distribution et coordination de tâches
6. **Évaluateur-Optimiseur** : Évaluation et optimisation des performances

## Dépannage

### Problèmes courants

1. **Erreur de connexion à MongoDB** :
   - Vérifiez que le service MongoDB est en cours d'exécution
   - Vérifiez les identifiants dans le fichier .env

2. **Erreur d'accès à MinIO** :
   - Vérifiez que le service MinIO est en cours d'exécution
   - Vérifiez les identifiants dans le fichier .env

3. **Erreur lors de l'exécution d'un modèle** :
   - Vérifiez que la clé API Groq est correctement configurée
   - Vérifiez que le service Spark est en cours d'exécution

### Logs

Les logs de chaque service peuvent être consultés avec la commande :
```bash
docker-compose logs <service-name>
```

## Exemple de flux complet

Voici un exemple de flux complet d'utilisation de la plateforme :

1. **Ajout d'un modèle de classification d'images** :
   - Accédez à la page "Modèles"
   - Cliquez sur "Ajouter un modèle"
   - Remplissez les informations : Nom="Modèle de classification d'images", Type="Classification", Framework="PyTorch"
   - Téléchargez le fichier du modèle
   - Cliquez sur "Créer"

2. **Ajout d'un dataset d'images** :
   - Accédez à la page "Datasets"
   - Cliquez sur "Ajouter un dataset"
   - Remplissez les informations : Nom="Dataset d'images CIFAR-10", Type="Image"
   - Téléchargez le fichier du dataset
   - Cliquez sur "Créer"

3. **Création d'un déploiement** :
   - Accédez à la page "Déploiements"
   - Cliquez sur "Créer un déploiement"
   - Sélectionnez le modèle de classification d'images
   - Configurez les paramètres : Nom="Déploiement de classification d'images", Environnement="Production"
   - Cliquez sur "Déployer"

4. **Exécution du modèle** :
   - Accédez à la page "Exécutions"
   - Cliquez sur "Nouvelle exécution"
   - Sélectionnez le déploiement de classification d'images
   - Sélectionnez le dataset CIFAR-10
   - Configurez les paramètres : batch_size=32
   - Cliquez sur "Exécuter"

5. **Consultation des résultats** :
   - Attendez que l'exécution soit terminée
   - Cliquez sur l'exécution pour voir les détails
   - Consultez les métriques (précision, rappel, etc.)
   - Téléchargez les résultats pour une analyse plus approfondie

## Conclusion

Cette plateforme centralisée de modèles ML offre une solution complète pour gérer le cycle de vie des modèles d'apprentissage automatique, de leur création à leur déploiement et exécution. L'approche API-First avec le protocole MCP permet une standardisation des communications et une évolutivité de la plateforme.

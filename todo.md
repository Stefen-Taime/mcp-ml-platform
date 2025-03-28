# Liste des tâches pour le POC de plateforme centralisée de modèles ML

## Analyse et structure du projet
- [x] Créer la structure de base des dossiers
- [x] Définir le protocole MCP et ses interfaces
- [x] Créer un schéma d'architecture global

## Docker et configuration
- [x] Créer le fichier docker-compose.yml principal
- [x] Créer les Dockerfiles pour chaque service
- [x] Créer le fichier .env pour les variables d'environnement
- [x] Configurer Nginx pour le routage

## Frontend (Next.js)
- [x] Créer la structure de l'application Next.js
- [x] Implémenter les composants UI principaux
- [x] Développer les pages (Dashboard, Models, Deployments, Executions)
- [x] Implémenter les appels API vers l'API Gateway

## API Gateway et MCP Hub
- [x] Développer l'API Gateway en FastAPI
- [x] Implémenter le MCP Hub pour la gestion des serveurs MCP
- [x] Configurer les routes et la validation des requêtes
- [x] Implémenter les modèles d'agents (chaînage, portes, routage, etc.)

## Serveurs MCP spécialisés
- [x] Développer le Model MCP Server (gestion des modèles ML)
- [x] Développer le Data MCP Server (accès aux données)
- [x] Développer l'Execution MCP Server (exécution via Groq et Spark)
- [x] Implémenter les modèles d'agents (chaînage, portes, routage, etc.)

## Services de stockage et traitement
- [x] Configurer MinIO pour le stockage des modèles et résultats
- [x] Configurer MongoDB pour les métadonnées
- [ ] Configurer Mongo Express pour la gestion de MongoDB
- [x] Configurer Spark pour le traitement distribué

## Tests et documentation
- [x] Tester le déploiement complet avec Docker Compose
- [x] Documenter l'architecture et les composants
- [x] Créer un guide d'utilisation
- [x] Documenter un exemple de flux complet

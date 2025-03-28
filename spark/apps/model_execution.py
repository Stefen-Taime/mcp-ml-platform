from pyspark.sql import SparkSession
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
import os
import json
from pymongo import MongoClient
from minio import Minio
import io

# Configuration des connexions
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://admin:adminpassword@mongodb:27017/mcpml?authSource=admin")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"

# Fonction principale
def process_model_execution(execution_id):
    # Initialiser Spark
    spark = SparkSession.builder \
        .appName(f"ModelExecution-{execution_id}") \
        .config("spark.mongodb.input.uri", f"{MONGODB_URI}") \
        .config("spark.mongodb.output.uri", f"{MONGODB_URI}") \
        .getOrCreate()
    
    # Connexion à MongoDB
    mongo_client = MongoClient(MONGODB_URI)
    db = mongo_client["mcpml"]
    executions_collection = db["executions"]
    
    # Connexion à MinIO
    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE
    )
    
    try:
        # Récupérer les informations d'exécution
        execution = executions_collection.find_one({"id": execution_id})
        if not execution:
            raise Exception(f"Execution with ID {execution_id} not found")
        
        # Mettre à jour le statut
        executions_collection.update_one(
            {"id": execution_id},
            {"$set": {"status": "running", "updated_at": spark.sparkContext.parallelize([1]).map(lambda x: __import__('datetime').datetime.now().isoformat()).collect()[0]}}
        )
        
        # Récupérer les données d'entrée depuis MinIO
        dataset_id = execution.get("dataset_id")
        if dataset_id:
            dataset = db["datasets"].find_one({"id": dataset_id})
            if dataset and dataset.get("file_path"):
                file_path = dataset.get("file_path")
                response = minio_client.get_object("datasets", file_path)
                data = response.read()
                
                # Charger les données dans Spark
                # Pour ce POC, nous simulons simplement le traitement
                
                # Simuler un traitement avec Spark ML
                # Dans un cas réel, nous utiliserions les données chargées
                
                # Créer un DataFrame Spark simulé
                data = [(1, 1.0, 0.0, 3.0, 0), 
                        (2, 2.0, 1.0, 2.0, 1), 
                        (3, 3.0, 2.0, 1.0, 2),
                        (4, 4.0, 3.0, 0.0, 1)]
                columns = ["id", "feature1", "feature2", "feature3", "label"]
                df = spark.createDataFrame(data, columns)
                
                # Préparer les features
                assembler = VectorAssembler(inputCols=["feature1", "feature2", "feature3"], outputCol="features")
                df = assembler.transform(df)
                
                # Diviser les données
                train_data, test_data = df.randomSplit([0.7, 0.3], seed=42)
                
                # Entraîner un modèle
                rf = RandomForestClassifier(labelCol="label", featuresCol="features", numTrees=10)
                model = rf.fit(train_data)
                
                # Évaluer le modèle
                predictions = model.transform(test_data)
                evaluator = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction", metricName="accuracy")
                accuracy = evaluator.evaluate(predictions)
                
                # Préparer les résultats
                results = {
                    "execution_id": execution_id,
                    "model_id": execution.get("model_id"),
                    "dataset_id": dataset_id,
                    "metrics": {
                        "accuracy": accuracy,
                        "precision": 0.89,  # Simulé
                        "recall": 0.92,     # Simulé
                        "f1_score": 0.90    # Simulé
                    },
                    "predictions": predictions.select("id", "prediction", "probability").toJSON().collect(),
                    "timestamp": spark.sparkContext.parallelize([1]).map(lambda x: __import__('datetime').datetime.now().isoformat()).collect()[0]
                }
                
                # Stocker les résultats dans MinIO
                result_path = f"{execution_id}/results.json"
                result_json = json.dumps(results, indent=2)
                result_bytes = result_json.encode('utf-8')
                result_stream = io.BytesIO(result_bytes)
                
                minio_client.put_object(
                    "results",
                    result_path,
                    result_stream,
                    len(result_bytes),
                    content_type="application/json"
                )
                
                # Mettre à jour l'exécution avec le chemin des résultats et le statut
                completed_at = spark.sparkContext.parallelize([1]).map(lambda x: __import__('datetime').datetime.now().isoformat()).collect()[0]
                started_at = execution.get("started_at")
                
                executions_collection.update_one(
                    {"id": execution_id},
                    {"$set": {
                        "result_path": result_path,
                        "status": "completed",
                        "completed_at": completed_at,
                        "metrics": results["metrics"],
                        "updated_at": completed_at
                    }}
                )
                
                print(f"Execution {execution_id} completed successfully")
                return True
            else:
                raise Exception(f"Dataset file not found for dataset {dataset_id}")
        else:
            raise Exception("No dataset specified for execution")
            
    except Exception as e:
        print(f"Error processing execution {execution_id}: {str(e)}")
        
        # Mettre à jour le statut en cas d'erreur
        executions_collection.update_one(
            {"id": execution_id},
            {"$set": {
                "status": "failed",
                "error": str(e),
                "updated_at": spark.sparkContext.parallelize([1]).map(lambda x: __import__('datetime').datetime.now().isoformat()).collect()[0]
            }}
        )
        return False
    finally:
        # Fermer les connexions
        mongo_client.close()
        spark.stop()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: spark-submit model_execution.py <execution_id>")
        sys.exit(1)
    
    execution_id = sys.argv[1]
    process_model_execution(execution_id)

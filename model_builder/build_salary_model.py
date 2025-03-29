#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour créer un modèle simple de prédiction de salaire.
Le modèle est enregistré au format .pkl pour être utilisé par
la plateforme MCP ML.
"""

import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
import os

# Créer le dossier models s'il n'existe pas
if not os.path.exists('models'):
    os.makedirs('models')

# Générer des données synthétiques pour l'exemple
np.random.seed(42)
n_samples = 1000

# Variables indépendantes (caractéristiques)
experience = np.random.randint(0, 20, n_samples)
education = np.random.randint(10, 22, n_samples)  # années d'éducation
hours_per_week = np.random.randint(20, 60, n_samples)
age = np.random.randint(22, 65, n_samples)

# Création d'une relation linéaire avec du bruit
salary = 20000 + 1500 * experience + 2000 * (education - 10) + 100 * hours_per_week + 5 * age
# Ajouter du bruit
salary = salary + np.random.normal(0, 5000, n_samples)

# Créer un DataFrame
data = pd.DataFrame({
    'experience': experience,
    'education': education,
    'hours_per_week': hours_per_week,
    'age': age,
    'salary': salary
})

# Diviser en features et target
X = data[['experience', 'education', 'hours_per_week', 'age']]
y = data['salary']

# Diviser en ensembles d'entraînement et de test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Créer un pipeline avec mise à l'échelle et régression linéaire
pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('regression', LinearRegression())
])

# Entraîner le modèle
pipeline.fit(X_train, y_train)

# Évaluer le modèle
train_score = pipeline.score(X_train, y_train)
test_score = pipeline.score(X_test, y_test)

print(f"Score R² sur l'ensemble d'entraînement: {train_score:.3f}")
print(f"Score R² sur l'ensemble de test: {test_score:.3f}")

# Faire une prédiction d'exemple
sample = pd.DataFrame({
    'experience': [5],
    'education': [16],
    'hours_per_week': [40],
    'age': [30]
})
prediction = pipeline.predict(sample)
print(f"Prédiction de salaire pour l'exemple: {prediction[0]:.2f}")

# Enregistrer le modèle entraîné
model_path = 'models/salary_prediction_model.pkl'
joblib.dump(pipeline, model_path)
print(f"Modèle enregistré dans {model_path}")

# Créer également un ensemble de données pour les tests futurs
test_data_path = 'models/salary_test_data.csv'
data.to_csv(test_data_path, index=False)
print(f"Données de test enregistrées dans {test_data_path}")
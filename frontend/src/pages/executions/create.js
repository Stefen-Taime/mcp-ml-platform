import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import Card from '../../components/Card';
import Button from '../../components/Button';
import LoadingSpinner from '../../components/LoadingSpinner';
import { executionsApi, deploymentsApi, datasetsApi } from '../../lib/api';

export default function CreateExecution() {
  const router = useRouter();
  const { deploymentId, cloneFrom } = router.query;
  const [deployments, setDeployments] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  
  const [formData, setFormData] = useState({
    deployment_id: '',
    dataset_id: '',
    parameters: {}
  });

  useEffect(() => {
    // Charger les déploiements actifs et les datasets
    async function loadData() {
      setIsLoading(true);
      try {
        // Charger les déploiements
        const deploymentsData = await deploymentsApi.getAll();
        const activeDeployments = deploymentsData.filter(d => d.status === 'active');
        setDeployments(activeDeployments);
        
        // Charger les datasets
        const datasetsData = await datasetsApi.getAll();
        setDatasets(datasetsData);
        
        // Si un deploymentId est fourni dans l'URL, présélectionner ce déploiement
        if (deploymentId && activeDeployments.length > 0) {
          const selectedDeployment = activeDeployments.find(d => d.id === deploymentId);
          if (selectedDeployment) {
            setFormData(prev => ({ ...prev, deployment_id: selectedDeployment.id }));
          }
        }
        
        // Si cloneFrom est fourni, charger les paramètres de cette exécution
        if (cloneFrom) {
          const execution = await executionsApi.getById(cloneFrom);
          if (execution) {
            setFormData(prev => ({
              ...prev,
              deployment_id: execution.deployment_id,
              dataset_id: execution.dataset_id || '',
              parameters: execution.parameters || {}
            }));
          }
        }
      } catch (err) {
        console.error('Error loading data:', err);
        setError('Erreur lors du chargement des données');
      } finally {
        setIsLoading(false);
      }
    }
    
    loadData();
  }, [deploymentId, cloneFrom]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };
  
  const handleParameterChange = (e) => {
    const { name, value } = e.target;
    let parsedValue = value;
    
    // Tenter de convertir les valeurs numériques
    if (!isNaN(value) && value !== '') {
      parsedValue = Number(value);
    }
    
    setFormData(prev => ({
      ...prev,
      parameters: {
        ...prev.parameters,
        [name]: parsedValue
      }
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    
    try {
      // Création de l'exécution
      await executionsApi.create(formData);
      router.push('/executions');
    } catch (err) {
      console.error('Error creating execution:', err);
      setError('Une erreur est survenue lors de la création de l\'exécution');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Layout>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Nouvelle exécution</h1>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      ) : (
        <Card>
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700">Déploiement</label>
              {deployments.length === 0 ? (
                <div className="mt-1 text-sm text-red-500">
                  Aucun déploiement actif disponible. Veuillez d'abord activer un déploiement.
                </div>
              ) : (
                <select
                  name="deployment_id"
                  value={formData.deployment_id}
                  onChange={handleChange}
                  required
                  className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
                >
                  <option value="">Sélectionnez un déploiement</option>
                  {deployments.map(deployment => (
                    <option key={deployment.id} value={deployment.id}>
                      {deployment.name} (Modèle: {deployment.model_name})
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Dataset (optionnel)</label>
              <select
                name="dataset_id"
                value={formData.dataset_id}
                onChange={handleChange}
                className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
              >
                <option value="">Sélectionnez un dataset</option>
                {datasets.map(dataset => (
                  <option key={dataset.id} value={dataset.id}>
                    {dataset.name} ({dataset.type}, {dataset.format})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Paramètres</label>
              <div className="mt-2 space-y-4 bg-gray-50 p-4 rounded-md">
                {/* Paramètres communs */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-500">Batch Size</label>
                    <input
                      type="number"
                      name="batch_size"
                      value={formData.parameters.batch_size || ''}
                      onChange={handleParameterChange}
                      className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500">Learning Rate</label>
                    <input
                      type="number"
                      name="learning_rate"
                      value={formData.parameters.learning_rate || ''}
                      onChange={handleParameterChange}
                      step="0.001"
                      className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500">Epochs</label>
                    <input
                      type="number"
                      name="epochs"
                      value={formData.parameters.epochs || ''}
                      onChange={handleParameterChange}
                      className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500">Seed</label>
                    <input
                      type="number"
                      name="seed"
                      value={formData.parameters.seed || ''}
                      onChange={handleParameterChange}
                      className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
                    />
                  </div>
                </div>
                
                {/* Paramètres avancés */}
                <div className="mt-4">
                  <label className="block text-xs font-medium text-gray-500">Paramètres avancés (JSON)</label>
                  <textarea
                    name="advanced_params"
                    value={formData.parameters.advanced_params || ''}
                    onChange={handleParameterChange}
                    rows="3"
                    placeholder="{}"
                    className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm font-mono text-sm"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-4">
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => router.back()}
                disabled={isSubmitting}
              >
                Annuler
              </Button>
              <Button 
                type="submit" 
                disabled={isSubmitting || deployments.length === 0 || !formData.deployment_id}
              >
                {isSubmitting ? 'Démarrage en cours...' : 'Démarrer l\'exécution'}
              </Button>
            </div>
          </form>
        </Card>
      )}
    </Layout>
  );
}
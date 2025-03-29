import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import Card from '../../components/Card';
import Button from '../../components/Button';
import LoadingSpinner from '../../components/LoadingSpinner';
import { deploymentsApi, modelsApi } from '../../lib/api';

export default function CreateDeployment() {
  const router = useRouter();
  const { modelId } = router.query;
  const [models, setModels] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    model_id: '',
    model_name: '',
    environment: 'development',
    status: 'inactive'
  });

  useEffect(() => {
    // Charger la liste des modèles disponibles
    async function loadModels() {
      setIsLoading(true);
      try {
        const data = await modelsApi.getAll();
        setModels(data);
        
        // Si un modelId est fourni dans l'URL, présélectionner ce modèle
        if (modelId && data.length > 0) {
          const selectedModel = data.find(m => m.id === modelId);
          if (selectedModel) {
            setFormData(prev => ({
              ...prev,
              model_id: selectedModel.id,
              model_name: selectedModel.name
            }));
          }
        }
      } catch (err) {
        setError('Erreur lors du chargement des modèles');
      } finally {
        setIsLoading(false);
      }
    }
    
    loadModels();
  }, [modelId]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    // Si le modèle change, mettre à jour model_name également
    if (name === 'model_id') {
      const selectedModel = models.find(m => m.id === value);
      if (selectedModel) {
        setFormData(prev => ({ ...prev, model_name: selectedModel.name }));
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    
    try {
      await deploymentsApi.create(formData);
      router.push('/deployments');
    } catch (err) {
      console.error('Error creating deployment:', err);
      setError('Une erreur est survenue lors de la création du déploiement');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Layout>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Créer un déploiement</h1>
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
              <label className="block text-sm font-medium text-gray-700">Nom</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
                className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Description</label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleChange}
                rows="3"
                className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Modèle</label>
              <select
                name="model_id"
                value={formData.model_id}
                onChange={handleChange}
                required
                className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
              >
                <option value="">Sélectionnez un modèle</option>
                {models.map(model => (
                  <option key={model.id} value={model.id}>
                    {model.name} ({model.framework}, {model.type})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Environnement</label>
              <select
                name="environment"
                value={formData.environment}
                onChange={handleChange}
                className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
              >
                <option value="development">Développement</option>
                <option value="staging">Pré-production</option>
                <option value="production">Production</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Statut</label>
              <select
                name="status"
                value={formData.status}
                onChange={handleChange}
                className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
              >
                <option value="inactive">Inactif</option>
                <option value="active">Actif</option>
              </select>
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
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Création en cours...' : 'Créer le déploiement'}
              </Button>
            </div>
          </form>
        </Card>
      )}
    </Layout>
  );
}
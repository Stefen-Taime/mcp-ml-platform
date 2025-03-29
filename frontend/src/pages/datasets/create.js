import React, { useState } from 'react';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import Card from '../../components/Card';
import Button from '../../components/Button';
import { datasetsApi } from '../../lib/api';

export default function CreateDataset() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [file, setFile] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    type: 'tabular',
    format: 'CSV'
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      
      // Auto-détection du format basée sur l'extension
      const extension = selectedFile.name.split('.').pop().toUpperCase();
      if (['CSV', 'JSON', 'TXT', 'PARQUET', 'AVRO'].includes(extension)) {
        setFormData(prev => ({ ...prev, format: extension }));
      }
      
      // Mise à jour de la taille
      setFormData(prev => ({ ...prev, size: selectedFile.size }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    
    try {
      // Étape 1: Créer le dataset
      const dataset = await datasetsApi.create(formData);
      
      // Étape 2: Si un fichier est sélectionné, le télécharger
      if (file && dataset.id) {
        await datasetsApi.upload(dataset.id, file);
      }
      
      router.push('/datasets');
    } catch (err) {
      console.error('Error creating dataset:', err);
      setError('Une erreur est survenue lors de la création du dataset');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Layout>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Ajouter un dataset</h1>
      </div>

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
            <label className="block text-sm font-medium text-gray-700">Type</label>
            <select
              name="type"
              value={formData.type}
              onChange={handleChange}
              className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
            >
              <option value="tabular">Tabulaire</option>
              <option value="image">Image</option>
              <option value="text">Texte</option>
              <option value="audio">Audio</option>
              <option value="video">Vidéo</option>
              <option value="time_series">Série temporelle</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Format</label>
            <select
              name="format"
              value={formData.format}
              onChange={handleChange}
              className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
            >
              <option value="CSV">CSV</option>
              <option value="JSON">JSON</option>
              <option value="PARQUET">Parquet</option>
              <option value="AVRO">Avro</option>
              <option value="TXT">Texte</option>
              <option value="PNG">PNG</option>
              <option value="JPG">JPG</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Fichier (optionnel)</label>
            <input
              type="file"
              onChange={handleFileChange}
              className="mt-1 block w-full p-2 border border-gray-300 rounded-md shadow-sm"
            />
            <p className="mt-1 text-sm text-gray-500">
              Vous pouvez télécharger un fichier maintenant ou le faire plus tard.
            </p>
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
              {isSubmitting ? 'Création en cours...' : 'Ajouter le dataset'}
            </Button>
          </div>
        </form>
      </Card>
    </Layout>
  );
}
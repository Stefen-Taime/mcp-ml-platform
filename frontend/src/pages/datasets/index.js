import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import Card from '../../components/Card';
import Button from '../../components/Button';
import LoadingSpinner from '../../components/LoadingSpinner';
import EmptyState from '../../components/EmptyState';
import { useDatasets } from '../../hooks/api-hooks';

export default function Datasets() {
  const router = useRouter();
  const { datasets, isLoading, isError, mutate } = useDatasets();
  const [searchTerm, setSearchTerm] = useState('');
  
  // Déboguer les données des datasets
  useEffect(() => {
    console.log('Datasets loaded:', datasets);
  }, [datasets]);
  
  const handleDatasetClick = (datasetId) => {
    console.log('Clicking on dataset:', datasetId);
    router.push(`/datasets/${datasetId}`);
  };
  
  const filteredDatasets = datasets?.filter(dataset => 
    dataset.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    dataset.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    dataset.type?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    dataset.format?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <Layout>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Datasets</h1>
          <p className="mt-2 text-gray-600">Gérez vos jeux de données</p>
        </div>
        <Button onClick={() => router.push('/datasets/create')}>
          Ajouter un dataset
        </Button>
      </div>

      <Card className="mb-6">
        <div className="flex items-center">
          <div className="relative flex-grow">
            <input
              type="text"
              className="input-field w-full pl-10"
              placeholder="Rechercher un dataset..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>
        </div>
      </Card>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      ) : isError ? (
        <Card>
          <div className="text-center py-6">
            <p className="text-red-500">Une erreur est survenue lors du chargement des datasets.</p>
            <Button className="mt-4" onClick={() => mutate()}>
              Réessayer
            </Button>
          </div>
        </Card>
      ) : filteredDatasets?.length === 0 ? (
        <EmptyState
          title="Aucun dataset trouvé"
          description={searchTerm ? "Aucun dataset ne correspond à votre recherche." : "Commencez par ajouter un dataset à votre plateforme."}
          action={
            <Button onClick={() => router.push('/datasets/create')}>
              Ajouter un dataset
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredDatasets?.map((dataset) => (
            <div key={dataset.id} onClick={() => handleDatasetClick(dataset.id)}>
              <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">{dataset.name}</h3>
                  <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded">
                    {dataset.type}
                  </span>
                </div>
                <p className="text-gray-600 text-sm mb-4 line-clamp-2">{dataset.description}</p>
                <div className="flex justify-between text-sm text-gray-500">
                  <div>Format: {dataset.format}</div>
                  <div>{(dataset.size / 1000000).toFixed(2)} MB</div>
                </div>
              </Card>
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
}
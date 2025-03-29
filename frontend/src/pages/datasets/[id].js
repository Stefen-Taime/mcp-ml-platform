import React from 'react';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import Card from '../../components/Card';
import Button from '../../components/Button';
import LoadingSpinner from '../../components/LoadingSpinner';
import { useDataset } from '../../hooks/api-hooks';

export default function DatasetDetail() {
  const router = useRouter();
  const { id } = router.query;
  const { dataset, isLoading, isError } = useDataset(id);

  if (isLoading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      </Layout>
    );
  }

  if (isError) {
    return (
      <Layout>
        <Card>
          <div className="text-center py-6">
            <p className="text-red-500">Une erreur est survenue lors du chargement du dataset.</p>
            <Button className="mt-4" onClick={() => router.back()}>
              Retour
            </Button>
          </div>
        </Card>
      </Layout>
    );
  }

  if (!dataset) {
    return (
      <Layout>
        <Card>
          <div className="text-center py-6">
            <p>Chargement du dataset...</p>
          </div>
        </Card>
      </Layout>
    );
  }

  // Formatage de la taille du fichier en unités lisibles
  const formatFileSize = (sizeInBytes) => {
    if (sizeInBytes < 1024) {
      return `${sizeInBytes} B`;
    } else if (sizeInBytes < 1024 * 1024) {
      return `${(sizeInBytes / 1024).toFixed(2)} KB`;
    } else if (sizeInBytes < 1024 * 1024 * 1024) {
      return `${(sizeInBytes / (1024 * 1024)).toFixed(2)} MB`;
    } else {
      return `${(sizeInBytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    }
  };

  return (
    <Layout>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{dataset.name}</h1>
          <p className="mt-2 text-gray-600">{dataset.description}</p>
        </div>
        <div className="space-x-4">
          <Button variant="outline" onClick={() => router.push(`/datasets/${dataset.id}/edit`)}>
            Modifier
          </Button>
          <Button onClick={() => router.push(`/executions/create?datasetId=${dataset.id}`)}>
            Utiliser ce dataset
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <Card>
          <h2 className="text-xl font-semibold mb-4">Informations générales</h2>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="font-medium">ID</span>
              <span>{dataset.id}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Type</span>
              <span>{dataset.type}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Format</span>
              <span>{dataset.format}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Taille</span>
              <span>{formatFileSize(dataset.size)}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Créé le</span>
              <span>{new Date(dataset.created_at).toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Mis à jour le</span>
              <span>{new Date(dataset.updated_at).toLocaleString()}</span>
            </div>
          </div>
        </Card>

        <Card>
          <h2 className="text-xl font-semibold mb-4">Actions</h2>
          <div className="space-y-4">
            <Button 
              className="w-full"
              onClick={() => router.push(`/datasets/${dataset.id}/visualize`)}
            >
              Visualiser les données
            </Button>
            
            <Button 
              className="w-full"
              onClick={() => router.push(`/datasets/${dataset.id}/transform`)}
            >
              Transformer les données
            </Button>
            
            <Button 
              className="w-full" 
              variant="outline"
              onClick={() => {
                // Logique pour télécharger le fichier
                alert(`Téléchargement du fichier ${dataset.file_name || 'dataset'}`);
              }}
            >
              Télécharger
            </Button>
            
            <Button 
              className="w-full" 
              variant="danger"
              onClick={() => {
                if (confirm('Êtes-vous sûr de vouloir supprimer ce dataset ? Cette action est irréversible.')) {
                  // Logique pour supprimer le dataset
                  alert(`Suppression du dataset ${dataset.id}`);
                  router.push('/datasets');
                }
              }}
            >
              Supprimer
            </Button>
          </div>
        </Card>
      </div>

      {dataset.transformations && dataset.transformations.length > 0 && (
        <Card>
          <h2 className="text-xl font-semibold mb-4">Transformations appliquées</h2>
          <div className="bg-gray-50 p-4 rounded-md">
            <pre className="whitespace-pre-wrap text-sm">
              {JSON.stringify(dataset.transformations, null, 2)}
            </pre>
          </div>
        </Card>
      )}

      {dataset.source_dataset_id && (
        <div className="mt-6">
          <Button variant="outline" onClick={() => router.push(`/datasets/${dataset.source_dataset_id}`)}>
            Voir le dataset source
          </Button>
        </div>
      )}
    </Layout>
  );
}
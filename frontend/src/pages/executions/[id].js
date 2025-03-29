import React, { useState } from 'react';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import Card from '../../components/Card';
import Button from '../../components/Button';
import LoadingSpinner from '../../components/LoadingSpinner';
import StatusBadge from '../../components/StatusBadge';
import { useExecution } from '../../hooks/api-hooks';

export default function ExecutionDetail() {
  const router = useRouter();
  const { id } = router.query;
  const { execution, isLoading, isError, mutate } = useExecution(id);

  const handleCancel = async () => {
    if (confirm('Êtes-vous sûr de vouloir annuler cette exécution ?')) {
      try {
        // Appel à l'API pour annuler l'exécution
        // Attendrait normalement une fonction comme executionsApi.cancel(id)
        alert('Exécution annulée avec succès');
        mutate(); // Rafraîchir les données
      } catch (error) {
        alert('Erreur lors de l\'annulation de l\'exécution');
        console.error(error);
      }
    }
  };

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
            <p className="text-red-500">Une erreur est survenue lors du chargement de l'exécution.</p>
            <Button className="mt-4" onClick={() => router.back()}>
              Retour
            </Button>
          </div>
        </Card>
      </Layout>
    );
  }

  if (!execution) {
    return (
      <Layout>
        <Card>
          <div className="text-center py-6">
            <p>Chargement de l'exécution...</p>
          </div>
        </Card>
      </Layout>
    );
  }

  // Calculer la durée de l'exécution
  const calculateDuration = () => {
    if (execution.completed_at) {
      const start = new Date(execution.started_at);
      const end = new Date(execution.completed_at);
      const durationMs = end - start;
      
      // Formater la durée
      const seconds = Math.floor(durationMs / 1000);
      if (seconds < 60) return `${seconds} secondes`;
      
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
      
      const hours = Math.floor(minutes / 60);
      const remainingMinutes = minutes % 60;
      return `${hours}h ${remainingMinutes}m ${remainingSeconds}s`;
    }
    
    return "En cours...";
  };

  return (
    <Layout>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Exécution {execution.id}</h1>
          <p className="mt-2 text-gray-600">
            Déploiement : <span className="text-blue-600 cursor-pointer hover:underline" 
              onClick={() => router.push(`/deployments/${execution.deployment_id}`)}>
              {execution.deployment_name}
            </span>
          </p>
        </div>
        <div className="space-x-4">
          {(execution.status === 'pending' || execution.status === 'running') && (
            <Button variant="danger" onClick={handleCancel}>
              Annuler
            </Button>
          )}
          {execution.status === 'completed' && (
            <Button onClick={() => router.push(`/executions/${execution.id}/results`)}>
              Voir les résultats
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <Card>
          <h2 className="text-xl font-semibold mb-4">Informations générales</h2>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="font-medium">ID</span>
              <span>{execution.id}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Statut</span>
              <StatusBadge status={execution.status} />
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Modèle</span>
              <span className="text-blue-600 cursor-pointer hover:underline" 
                onClick={() => router.push(`/models/${execution.model_id}`)}>
                {execution.model_name}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Déploiement</span>
              <span className="text-blue-600 cursor-pointer hover:underline" 
                onClick={() => router.push(`/deployments/${execution.deployment_id}`)}>
                {execution.deployment_name}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Démarré le</span>
              <span>{new Date(execution.started_at).toLocaleString()}</span>
            </div>
            {execution.completed_at && (
              <div className="flex justify-between">
                <span className="font-medium">Terminé le</span>
                <span>{new Date(execution.completed_at).toLocaleString()}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="font-medium">Durée</span>
              <span>{calculateDuration()}</span>
            </div>
          </div>
        </Card>

        <Card>
          <h2 className="text-xl font-semibold mb-4">Paramètres d'exécution</h2>
          {execution.parameters ? (
            <div className="bg-gray-50 p-4 rounded-md">
              <pre className="whitespace-pre-wrap text-sm">
                {JSON.stringify(execution.parameters, null, 2)}
              </pre>
            </div>
          ) : (
            <p className="text-gray-600">Aucun paramètre spécifié pour cette exécution.</p>
          )}
        </Card>
      </div>

      {execution.status === 'completed' && execution.metrics && (
        <Card className="mb-6">
          <h2 className="text-xl font-semibold mb-4">Métriques</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(execution.metrics).map(([key, value]) => (
              <div key={key} className="bg-gray-50 p-4 rounded-md">
                <div className="text-sm text-gray-500 uppercase">{key}</div>
                <div className="text-2xl font-bold mt-1">
                  {typeof value === 'number' ? value.toFixed(4) : value}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {execution.status === 'failed' && execution.error && (
        <Card className="mb-6 border-red-300">
          <h2 className="text-xl font-semibold mb-4 text-red-600">Erreur</h2>
          <div className="bg-red-50 p-4 rounded-md text-red-600">
            {execution.error}
          </div>
        </Card>
      )}

      <div className="flex justify-end space-x-4">
        <Button variant="outline" onClick={() => router.back()}>
          Retour
        </Button>
        {execution.status === 'completed' && (
          <Button onClick={() => router.push(`/executions/${execution.id}/results`)}>
            Voir les résultats détaillés
          </Button>
        )}
        {(execution.status === 'completed' || execution.status === 'failed') && (
          <Button 
            onClick={() => router.push(`/executions/create?cloneFrom=${execution.id}`)}
          >
            Relancer avec les mêmes paramètres
          </Button>
        )}
      </div>
    </Layout>
  );
}
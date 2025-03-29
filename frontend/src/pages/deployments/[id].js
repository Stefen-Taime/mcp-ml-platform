import React, { useState } from 'react';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import Card from '../../components/Card';
import Button from '../../components/Button';
import LoadingSpinner from '../../components/LoadingSpinner';
import StatusBadge from '../../components/StatusBadge';
import { useDeployment, useExecutions } from '../../hooks/api-hooks';

export default function DeploymentDetail() {
  const router = useRouter();
  const { id } = router.query;
  const { deployment, isLoading, isError } = useDeployment(id);
  const { executions } = useExecutions();
  
  // Filtrer les exécutions pour ce déploiement
  const deploymentExecutions = executions?.filter(execution => 
    execution.deployment_id === id
  ).sort((a, b) => new Date(b.started_at) - new Date(a.started_at));

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
            <p className="text-red-500">Une erreur est survenue lors du chargement du déploiement.</p>
            <Button className="mt-4" onClick={() => router.back()}>
              Retour
            </Button>
          </div>
        </Card>
      </Layout>
    );
  }

  if (!deployment) {
    return (
      <Layout>
        <Card>
          <div className="text-center py-6">
            <p>Chargement du déploiement...</p>
          </div>
        </Card>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{deployment.name}</h1>
          <p className="mt-2 text-gray-600">{deployment.description}</p>
        </div>
        <div className="space-x-4">
          <Button variant="outline" onClick={() => router.push(`/deployments/${deployment.id}/edit`)}>
            Modifier
          </Button>
          <Button onClick={() => router.push(`/executions/create?deploymentId=${deployment.id}`)}>
            Exécuter
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <Card>
          <h2 className="text-xl font-semibold mb-4">Informations générales</h2>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="font-medium">ID</span>
              <span>{deployment.id}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Statut</span>
              <StatusBadge status={deployment.status} />
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Modèle</span>
              <span className="text-blue-600 cursor-pointer hover:underline" 
                onClick={() => router.push(`/models/${deployment.model_id}`)}>
                {deployment.model_name}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Environnement</span>
              <span>{deployment.environment}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Créé le</span>
              <span>{new Date(deployment.created_at).toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Mis à jour le</span>
              <span>{new Date(deployment.updated_at).toLocaleString()}</span>
            </div>
          </div>
        </Card>

        <Card>
          <h2 className="text-xl font-semibold mb-4">Actions</h2>
          <div className="space-y-4">
            <Button 
              className="w-full"
              disabled={deployment.status !== 'active'}
              onClick={() => router.push(`/executions/create?deploymentId=${deployment.id}`)}
            >
              Nouvelle exécution
            </Button>
            
            <Button 
              className="w-full" 
              variant={deployment.status === 'active' ? 'danger' : 'primary'}
              onClick={() => {
                /* Logique pour activer/désactiver le déploiement */
                alert(`${deployment.status === 'active' ? 'Désactivation' : 'Activation'} du déploiement ${deployment.id}`);
              }}
            >
              {deployment.status === 'active' ? 'Désactiver' : 'Activer'} le déploiement
            </Button>
            
            <Button 
              className="w-full" 
              variant="outline"
              onClick={() => router.push(`/deployments/${deployment.id}/edit`)}
            >
              Modifier le déploiement
            </Button>
          </div>
        </Card>
      </div>

      <Card>
        <h2 className="text-xl font-semibold mb-4">Dernières exécutions</h2>
        {!deploymentExecutions || deploymentExecutions.length === 0 ? (
          <p className="text-gray-600">
            Aucune exécution pour ce déploiement. Lancez une nouvelle exécution pour tester votre modèle.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Démarré le</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Terminé le</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {deploymentExecutions.slice(0, 5).map((execution) => (
                  <tr key={execution.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{execution.id}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={execution.status} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500">{new Date(execution.started_at).toLocaleString()}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500">
                        {execution.completed_at ? new Date(execution.completed_at).toLocaleString() : '-'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button 
                        className="text-blue-600 hover:text-blue-900 mr-3"
                        onClick={() => router.push(`/executions/${execution.id}`)}
                      >
                        Détails
                      </button>
                      {execution.status === 'completed' && (
                        <button 
                          className="text-green-600 hover:text-green-900"
                          onClick={() => router.push(`/executions/${execution.id}/results`)}
                        >
                          Résultats
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {deploymentExecutions.length > 5 && (
              <div className="mt-4 text-center">
                <Button 
                  variant="outline" 
                  onClick={() => router.push(`/executions?deploymentId=${deployment.id}`)}
                >
                  Voir toutes les exécutions
                </Button>
              </div>
            )}
          </div>
        )}
      </Card>
    </Layout>
  );
}
import React from 'react';
import { useRouter } from 'next/router';
import Layout from '../components/Layout';
import Card from '../components/Card';
import Button from '../components/Button';
import LoadingSpinner from '../components/LoadingSpinner';
import { useModels, useDeployments, useExecutions } from '../hooks/api-hooks';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

// Enregistrer les composants ChartJS
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export default function Dashboard() {
  const router = useRouter();
  const { models, isLoading: isLoadingModels } = useModels();
  const { deployments, isLoading: isLoadingDeployments } = useDeployments();
  const { executions, isLoading: isLoadingExecutions } = useExecutions();

  const isLoading = isLoadingModels || isLoadingDeployments || isLoadingExecutions;

  // Données pour le graphique des exécutions par statut
  const executionStatusData = {
    labels: ['Terminé', 'En cours', 'En attente', 'Échoué', 'Annulé'],
    datasets: [
      {
        label: 'Nombre d\'exécutions',
        data: [
          executions?.filter(e => e.status === 'completed').length || 0,
          executions?.filter(e => e.status === 'running').length || 0,
          executions?.filter(e => e.status === 'pending').length || 0,
          executions?.filter(e => e.status === 'failed').length || 0,
          executions?.filter(e => e.status === 'cancelled').length || 0,
        ],
        backgroundColor: [
          'rgba(54, 162, 235, 0.6)',
          'rgba(153, 102, 255, 0.6)',
          'rgba(255, 206, 86, 0.6)',
          'rgba(255, 99, 132, 0.6)',
          'rgba(255, 159, 64, 0.6)',
        ],
      },
    ],
  };

  // Options pour le graphique
  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Statut des exécutions',
      },
    },
  };

  // Récupérer les 5 dernières exécutions
  const recentExecutions = executions
    ? [...executions].sort((a, b) => new Date(b.started_at) - new Date(a.started_at)).slice(0, 5)
    : [];

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Tableau de bord</h1>
        <p className="mt-2 text-gray-600">Vue d'ensemble de votre plateforme de modèles ML</p>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      ) : (
        <>
          {/* Statistiques */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <Card className="text-center">
              <h3 className="text-lg font-medium text-gray-500">Modèles</h3>
              <p className="mt-2 text-4xl font-bold text-primary-600">{models?.length || 0}</p>
              <Button 
                className="mt-4" 
                onClick={() => router.push('/models')}
              >
                Voir tous les modèles
              </Button>
            </Card>
            
            <Card className="text-center">
              <h3 className="text-lg font-medium text-gray-500">Déploiements</h3>
              <p className="mt-2 text-4xl font-bold text-secondary-600">{deployments?.length || 0}</p>
              <Button 
                className="mt-4" 
                variant="secondary"
                onClick={() => router.push('/deployments')}
              >
                Voir tous les déploiements
              </Button>
            </Card>
            
            <Card className="text-center">
              <h3 className="text-lg font-medium text-gray-500">Exécutions</h3>
              <p className="mt-2 text-4xl font-bold text-green-600">{executions?.length || 0}</p>
              <Button 
                className="mt-4" 
                variant="success"
                onClick={() => router.push('/executions')}
              >
                Voir toutes les exécutions
              </Button>
            </Card>
          </div>

          {/* Graphique et exécutions récentes */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card title="Statut des exécutions">
              <div className="h-64">
                <Bar data={executionStatusData} options={chartOptions} />
              </div>
            </Card>
            
            <Card title="Exécutions récentes">
              {recentExecutions.length > 0 ? (
                <div className="divide-y divide-gray-200">
                  {recentExecutions.map((execution) => (
                    <div 
                      key={execution.id} 
                      className="py-3 flex justify-between items-center cursor-pointer hover:bg-gray-50"
                      onClick={() => router.push(`/executions/${execution.id}`)}
                    >
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {execution.model_name}
                        </p>
                        <p className="text-xs text-gray-500">
                          {new Date(execution.started_at).toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          execution.status === 'completed' ? 'bg-blue-100 text-blue-800' :
                          execution.status === 'running' ? 'bg-purple-100 text-purple-800' :
                          execution.status === 'failed' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {execution.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center py-4 text-gray-500">Aucune exécution récente</p>
              )}
              <div className="mt-4 text-center">
                <Button 
                  variant="outline"
                  onClick={() => router.push('/executions')}
                >
                  Voir toutes les exécutions
                </Button>
              </div>
            </Card>
          </div>
        </>
      )}
    </Layout>
  );
}

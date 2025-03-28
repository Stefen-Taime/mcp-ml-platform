import React, { useState } from 'react';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import Card from '../../components/Card';
import Button from '../../components/Button';
import LoadingSpinner from '../../components/LoadingSpinner';
import EmptyState from '../../components/EmptyState';
import DeploymentCard from '../../components/DeploymentCard';
import { useDeployments } from '../../hooks/api-hooks';

export default function Deployments() {
  const router = useRouter();
  const { deployments, isLoading, isError, mutate } = useDeployments();
  const [searchTerm, setSearchTerm] = useState('');
  
  const filteredDeployments = deployments?.filter(deployment => 
    deployment.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    deployment.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
    deployment.model_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    deployment.environment.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <Layout>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Déploiements</h1>
          <p className="mt-2 text-gray-600">Gérez vos déploiements de modèles</p>
        </div>
        <Button onClick={() => router.push('/deployments/create')}>
          Créer un déploiement
        </Button>
      </div>

      <Card className="mb-6">
        <div className="flex items-center">
          <div className="relative flex-grow">
            <input
              type="text"
              className="input-field w-full pl-10"
              placeholder="Rechercher un déploiement..."
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
            <p className="text-red-500">Une erreur est survenue lors du chargement des déploiements.</p>
            <Button className="mt-4" onClick={() => mutate()}>
              Réessayer
            </Button>
          </div>
        </Card>
      ) : filteredDeployments?.length === 0 ? (
        <EmptyState
          title="Aucun déploiement trouvé"
          description={searchTerm ? "Aucun déploiement ne correspond à votre recherche." : "Commencez par créer un déploiement pour vos modèles."}
          action={
            <Button onClick={() => router.push('/deployments/create')}>
              Créer un déploiement
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredDeployments?.map((deployment) => (
            <DeploymentCard
              key={deployment.id}
              deployment={deployment}
              onClick={() => router.push(`/deployments/${deployment.id}`)}
            />
          ))}
        </div>
      )}
    </Layout>
  );
}
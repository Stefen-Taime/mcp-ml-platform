import React, { useState } from 'react';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import Card from '../../components/Card';
import Button from '../../components/Button';
import LoadingSpinner from '../../components/LoadingSpinner';
import EmptyState from '../../components/EmptyState';
import ExecutionCard from '../../components/ExecutionCard';
import StatusBadge from '../../components/StatusBadge';
import { useExecutions } from '../../hooks/api-hooks';

export default function Executions() {
  const router = useRouter();
  const { executions, isLoading, isError, mutate } = useExecutions();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  
  const filteredExecutions = executions?.filter(execution => {
    const matchesSearch = 
      execution.id.toString().includes(searchTerm.toLowerCase()) ||
      execution.model_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      execution.deployment_name.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || execution.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  const sortedExecutions = filteredExecutions?.sort((a, b) => 
    new Date(b.started_at) - new Date(a.started_at)
  );

  return (
    <Layout>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Exécutions</h1>
          <p className="mt-2 text-gray-600">Suivez et gérez les exécutions de vos modèles</p>
        </div>
        <Button onClick={() => router.push('/executions/create')}>
          Nouvelle exécution
        </Button>
      </div>

      <Card className="mb-6">
        <div className="flex flex-col md:flex-row md:items-center gap-4">
          <div className="relative flex-grow">
            <input
              type="text"
              className="input-field w-full pl-10"
              placeholder="Rechercher une exécution..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>
          <div className="flex-shrink-0">
            <select
              className="input-field"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">Tous les statuts</option>
              <option value="pending">En attente</option>
              <option value="running">En cours</option>
              <option value="completed">Terminé</option>
              <option value="failed">Échoué</option>
              <option value="cancelled">Annulé</option>
            </select>
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
            <p className="text-red-500">Une erreur est survenue lors du chargement des exécutions.</p>
            <Button className="mt-4" onClick={() => mutate()}>
              Réessayer
            </Button>
          </div>
        </Card>
      ) : sortedExecutions?.length === 0 ? (
        <EmptyState
          title="Aucune exécution trouvée"
          description={searchTerm || statusFilter !== 'all' ? "Aucune exécution ne correspond à vos critères." : "Commencez par lancer une exécution de modèle."}
          action={
            <Button onClick={() => router.push('/executions/create')}>
              Nouvelle exécution
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {sortedExecutions?.map((execution) => (
            <ExecutionCard
              key={execution.id}
              execution={execution}
              onClick={() => router.push(`/executions/${execution.id}`)}
            />
          ))}
        </div>
      )}
    </Layout>
  );
}
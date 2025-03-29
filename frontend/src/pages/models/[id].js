// Créez ce fichier: src/pages/models/[id].js
import React, { useState } from 'react';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import Card from '../../components/Card';
import Button from '../../components/Button';
import LoadingSpinner from '../../components/LoadingSpinner';
import { useModel } from '../../hooks/api-hooks';

export default function ModelDetail() {
  const router = useRouter();
  const { id } = router.query;
  const { model, isLoading, isError } = useModel(id);

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
            <p className="text-red-500">Une erreur est survenue lors du chargement du modèle.</p>
            <Button className="mt-4" onClick={() => router.back()}>
              Retour
            </Button>
          </div>
        </Card>
      </Layout>
    );
  }

  if (!model) {
    return (
      <Layout>
        <Card>
          <div className="text-center py-6">
            <p>Chargement du modèle...</p>
          </div>
        </Card>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{model.name}</h1>
          <p className="mt-2 text-gray-600">{model.description}</p>
        </div>
        <div className="space-x-4">
          <Button variant="outline" onClick={() => router.push(`/models/${model.id}/edit`)}>
            Modifier
          </Button>
          <Button onClick={() => router.push(`/deployments/create?modelId=${model.id}`)}>
            Déployer
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <h2 className="text-xl font-semibold mb-4">Informations générales</h2>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="font-medium">ID</span>
              <span>{model.id}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Type</span>
              <span>{model.type}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Framework</span>
              <span>{model.framework}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Version</span>
              <span>{model.version}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Créé le</span>
              <span>{new Date(model.created_at).toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Mis à jour le</span>
              <span>{new Date(model.updated_at).toLocaleString()}</span>
            </div>
          </div>
        </Card>

        <Card>
          <h2 className="text-xl font-semibold mb-4">Déploiements</h2>
          <p className="text-gray-600">
            Consultez les déploiements de ce modèle ou créez un nouveau déploiement.
          </p>
          <div className="mt-4">
            <Button onClick={() => router.push(`/deployments?modelId=${model.id}`)}>
              Voir les déploiements
            </Button>
          </div>
        </Card>
      </div>
    </Layout>
  );
}
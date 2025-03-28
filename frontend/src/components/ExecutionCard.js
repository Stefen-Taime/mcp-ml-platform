import React from 'react';
import StatusBadge from './StatusBadge';

const ExecutionCard = ({ execution, onClick }) => {
  return (
    <div 
      className="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow cursor-pointer"
      onClick={onClick}
    >
      <div className="flex justify-between items-start">
        <h3 className="text-lg font-semibold text-gray-900">Exécution #{execution.id}</h3>
        <StatusBadge status={execution.status} />
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2">
        <div>
          <p className="text-xs font-medium text-gray-500">Déploiement</p>
          <p className="text-sm text-gray-900">{execution.deployment_name}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-gray-500">Modèle</p>
          <p className="text-sm text-gray-900">{execution.model_name}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-gray-500">Démarré le</p>
          <p className="text-sm text-gray-900">{new Date(execution.started_at).toLocaleString()}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-gray-500">Durée</p>
          <p className="text-sm text-gray-900">{execution.duration ? `${execution.duration}s` : 'En cours...'}</p>
        </div>
      </div>
    </div>
  );
};

export default ExecutionCard;

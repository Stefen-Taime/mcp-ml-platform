import React from 'react';
import StatusBadge from './StatusBadge';

const DeploymentCard = ({ deployment, onClick }) => {
  return (
    <div 
      className="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow cursor-pointer"
      onClick={onClick}
    >
      <div className="flex justify-between items-start">
        <h3 className="text-lg font-semibold text-gray-900">{deployment.name}</h3>
        <StatusBadge status={deployment.status} />
      </div>
      <p className="mt-2 text-sm text-gray-600 line-clamp-2">{deployment.description}</p>
      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center">
          <span className="text-xs font-medium text-gray-500">Modèle: {deployment.model_name}</span>
        </div>
        <div className="flex items-center">
          <span className="text-xs font-medium text-gray-500">Environnement: {deployment.environment}</span>
        </div>
      </div>
    </div>
  );
};

export default DeploymentCard;

import React from 'react';

const ModelCard = ({ model, onClick }) => {
  return (
    <div 
      className="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow cursor-pointer"
      onClick={onClick}
    >
      <h3 className="text-lg font-semibold text-gray-900">{model.name}</h3>
      <p className="mt-2 text-sm text-gray-600 line-clamp-2">{model.description}</p>
      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center">
          <span className="text-xs font-medium text-gray-500">Type: {model.type}</span>
        </div>
        <div className="flex items-center">
          <span className="text-xs font-medium text-gray-500">Framework: {model.framework}</span>
        </div>
      </div>
    </div>
  );
};

export default ModelCard;

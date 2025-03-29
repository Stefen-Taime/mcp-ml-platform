import React from 'react';
import Card from './Card';

export default function DatasetCard({ dataset, onClick }) {
  return (
    <Card 
      className="hover:shadow-lg transition-shadow cursor-pointer" 
      onClick={onClick}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">{dataset.name}</h3>
        <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded">
          {dataset.type}
        </span>
      </div>
      <p className="text-gray-600 text-sm mb-4 line-clamp-2">{dataset.description}</p>
      <div className="flex justify-between text-sm text-gray-500">
        <div>Format: {dataset.format}</div>
        <div>{(dataset.size / 1000000).toFixed(2)} MB</div>
      </div>
    </Card>
  );
}
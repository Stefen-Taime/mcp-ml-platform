import React from 'react';

const StatusBadge = ({ status }) => {
  const statusClasses = {
    active: 'bg-green-100 text-green-800',
    inactive: 'bg-gray-100 text-gray-800',
    pending: 'bg-yellow-100 text-yellow-800',
    failed: 'bg-red-100 text-red-800',
    completed: 'bg-blue-100 text-blue-800',
    running: 'bg-purple-100 text-purple-800',
    cancelled: 'bg-orange-100 text-orange-800'
  };

  const statusClass = statusClasses[status.toLowerCase()] || 'bg-gray-100 text-gray-800';

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusClass}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
};

export default StatusBadge;

import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API pour les modèles
export const modelsApi = {
  getAll: async () => {
    const response = await api.get('/models');
    return response.data;
  },
  getById: async (id) => {
    const response = await api.get(`/models/${id}`);
    return response.data;
  },
  create: async (modelData) => {
    const response = await api.post('/models', modelData);
    return response.data;
  },
  update: async (id, modelData) => {
    const response = await api.put(`/models/${id}`, modelData);
    return response.data;
  },
  delete: async (id) => {
    const response = await api.delete(`/models/${id}`);
    return response.data;
  },
  upload: async (id, file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post(`/models/${id}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

// API pour les déploiements
export const deploymentsApi = {
  getAll: async () => {
    const response = await api.get('/deployments');
    return response.data;
  },
  getById: async (id) => {
    const response = await api.get(`/deployments/${id}`);
    return response.data;
  },
  create: async (deploymentData) => {
    const response = await api.post('/deployments', deploymentData);
    return response.data;
  },
  update: async (id, deploymentData) => {
    const response = await api.put(`/deployments/${id}`, deploymentData);
    return response.data;
  },
  delete: async (id) => {
    const response = await api.delete(`/deployments/${id}`);
    return response.data;
  },
};

// API pour les exécutions
export const executionsApi = {
  getAll: async () => {
    const response = await api.get('/executions');
    return response.data;
  },
  getById: async (id) => {
    const response = await api.get(`/executions/${id}`);
    return response.data;
  },
  create: async (executionData) => {
    const response = await api.post('/executions', executionData);
    return response.data;
  },
  cancel: async (id) => {
    const response = await api.post(`/executions/${id}/cancel`);
    return response.data;
  },
  getResults: async (id) => {
    const response = await api.get(`/executions/${id}/results`);
    return response.data;
  },
  uploadData: async (id, file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post(`/executions/${id}/upload-data`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

// API pour les datasets
export const datasetsApi = {
  getAll: async () => {
    const response = await api.get('/datasets');
    return response.data;
  },
  getById: async (id) => {
    const response = await api.get(`/datasets/${id}`);
    return response.data;
  },
  create: async (datasetData) => {
    const response = await api.post('/datasets', datasetData);
    return response.data;
  },
  update: async (id, datasetData) => {
    const response = await api.put(`/datasets/${id}`, datasetData);
    return response.data;
  },
  delete: async (id) => {
    const response = await api.delete(`/datasets/${id}`);
    return response.data;
  },
  upload: async (id, file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post(`/datasets/${id}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

export default api;
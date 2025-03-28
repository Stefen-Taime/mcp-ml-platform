import { useState, useEffect } from 'react';
import useSWR from 'swr';
import api, { modelsApi, deploymentsApi, executionsApi, datasetsApi } from '../lib/api';

// Utilisation d'axios dans le fetcher SWR
const fetcher = (url) => api.get(url).then(res => res.data);

export function useModels() {
  const { data, error, mutate } = useSWR('models', fetcher);
  
  return {
    models: data,
    isLoading: !error && !data,
    isError: error,
    mutate
  };
}

export function useModel(id) {
  const { data, error, mutate } = useSWR(id ? `models/${id}` : null, fetcher);
  
  return {
    model: data,
    isLoading: !error && !data,
    isError: error,
    mutate
  };
}

export function useDeployments() {
  const { data, error, mutate } = useSWR('deployments', fetcher);
  
  return {
    deployments: data,
    isLoading: !error && !data,
    isError: error,
    mutate
  };
}

export function useDeployment(id) {
  const { data, error, mutate } = useSWR(id ? `deployments/${id}` : null, fetcher);
  
  return {
    deployment: data,
    isLoading: !error && !data,
    isError: error,
    mutate
  };
}

export function useExecutions() {
  const { data, error, mutate } = useSWR('executions', fetcher);
  
  return {
    executions: data,
    isLoading: !error && !data,
    isError: error,
    mutate
  };
}

export function useExecution(id) {
  const { data, error, mutate } = useSWR(id ? `executions/${id}` : null, fetcher);
  
  return {
    execution: data,
    isLoading: !error && !data,
    isError: error,
    mutate
  };
}

export function useDatasets() {
  const { data, error, mutate } = useSWR('datasets', fetcher);
  
  return {
    datasets: data,
    isLoading: !error && !data,
    isError: error,
    mutate
  };
}

export function useDataset(id) {
  const { data, error, mutate } = useSWR(id ? `datasets/${id}` : null, fetcher);
  
  return {
    dataset: data,
    isLoading: !error && !data,
    isError: error,
    mutate
  };
}
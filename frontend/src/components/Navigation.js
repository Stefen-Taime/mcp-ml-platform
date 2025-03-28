import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';

const Navigation = () => {
  const router = useRouter();
  
  const isActive = (path) => {
    return router.pathname === path ? 'bg-primary-700' : '';
  };

  return (
    <nav className="bg-primary-800 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Link href="/" className="text-xl font-bold">
                MCP ML Platform
              </Link>
            </div>
            <div className="hidden md:block">
              <div className="ml-10 flex items-baseline space-x-4">
                <Link href="/" className={`px-3 py-2 rounded-md text-sm font-medium ${isActive('/')}`}>
                  Dashboard
                </Link>
                <Link href="/models" className={`px-3 py-2 rounded-md text-sm font-medium ${isActive('/models')}`}>
                  Modèles
                </Link>
                <Link href="/deployments" className={`px-3 py-2 rounded-md text-sm font-medium ${isActive('/deployments')}`}>
                  Déploiements
                </Link>
                <Link href="/executions" className={`px-3 py-2 rounded-md text-sm font-medium ${isActive('/executions')}`}>
                  Exécutions
                </Link>
                <Link href="/datasets" className={`px-3 py-2 rounded-md text-sm font-medium ${isActive('/datasets')}`}>
                  Données
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;

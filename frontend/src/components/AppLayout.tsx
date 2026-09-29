'use client';

import { ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { useAuth } from '@/lib/auth';


export function AppLayout({ children, title, subtitle }: { children: ReactNode, title?: string, subtitle?: string }) {
  const { isAuthenticated, isLoading } = useAuth();
  
  if (isLoading) {
    return <div className="min-h-screen bg-background flex items-center justify-center">Carregando...</div>;
  }
  
  if (!isAuthenticated) {
    return null; // Will redirect in AuthProvider
  }

  return (
    <div className="bg-background text-on-surface antialiased font-body-md text-body-md min-h-screen flex">
      <Sidebar />
      <div className="pl-64 flex-1 flex flex-col min-w-0 bg-background">
        <header className="sticky top-0 z-30 flex items-center justify-between px-margin-desktop py-space-md w-full bg-surface-container-lowest border-b border-outline-variant">
          <div className="flex items-center gap-space-md">
            <div className="flex items-center gap-2 text-on-surface-variant font-label-md text-label-md">
              <span>Operações</span>
              <span className="text-outline">/</span>
              <span className="text-on-surface font-semibold">{title || 'Página'}</span>
            </div>
          </div>
          <div className="flex items-center gap-space-sm">
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-[11px] font-medium text-emerald-800 tracking-wider">MOTOR IA ONLINE</span>
            </div>
          </div>
        </header>

        <main className="flex-1 px-margin-desktop py-space-xl max-w-[1500px] w-full mx-auto space-y-space-xl">
          {title && (
            <div className="flex flex-col gap-1 border-b border-outline-variant pb-space-lg">
              <h1 className="font-headline-lg text-headline-lg font-bold text-on-surface tracking-tight">{title}</h1>
              {subtitle && (
                <p className="font-body-md text-body-md text-on-surface-variant max-w-3xl">
                  {subtitle}
                </p>
              )}
            </div>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}

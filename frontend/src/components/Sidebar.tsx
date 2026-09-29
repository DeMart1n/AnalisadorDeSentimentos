'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 flex flex-col justify-between p-space-md z-40 bg-surface-container-lowest border-r border-outline-variant select-none">
      <div className="flex flex-col gap-space-lg">
        {/* Brand */}
        <div className="flex items-center gap-space-sm px-space-xs py-space-xs">
          <div className="w-9 h-9 rounded-lg bg-primary-container text-on-primary flex items-center justify-center shadow-sm">
            <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>space_dashboard</span>
          </div>
          <div className="flex flex-col">
            <span className="font-headline-md text-headline-md font-bold text-on-surface leading-none">SentimentIQ</span>
            <span className="font-label-sm text-label-sm text-outline mt-1 font-medium">CX Intelligence</span>
          </div>
        </div>

        {/* Navigation */}
        <nav aria-label="Menu Principal" className="flex flex-col gap-1.5">
          <Link 
            href="/"
            className={`flex items-center gap-space-sm px-space-md py-space-sm rounded-lg font-label-md text-label-md transition-colors duration-150 ${
              pathname === '/' 
                ? 'bg-surface-container-low text-primary font-semibold' 
                : 'text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined">space_dashboard</span>
            <span>Dashboard</span>
            {pathname === '/' && <span className="ml-auto w-1.5 h-4 bg-primary rounded-full"></span>}
          </Link>

          {user?.role === 'ADMIN' && (
            <Link 
              href="/upload"
              className={`flex items-center gap-space-sm px-space-md py-space-sm rounded-lg font-label-md text-label-md transition-colors duration-150 ${
                pathname === '/upload' 
                  ? 'bg-surface-container-low text-primary font-semibold' 
                  : 'text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined" style={pathname === '/upload' ? { fontVariationSettings: "'FILL' 1" } : {}}>upload_file</span>
              <span>Inserir Conversas</span>
              {pathname === '/upload' && <span className="ml-auto w-1.5 h-4 bg-primary rounded-full"></span>}
            </Link>
          )}

          <Link 
            href="/conversas"
            className={`flex items-center gap-space-sm px-space-md py-space-sm rounded-lg font-label-md text-label-md transition-colors duration-150 ${
              pathname === '/conversas' || pathname.startsWith('/conversas/')
                ? 'bg-surface-container-low text-primary font-semibold' 
                : 'text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined">forum</span>
            <span>Conversas</span>
            {(pathname === '/conversas' || pathname.startsWith('/conversas/')) && <span className="ml-auto w-1.5 h-4 bg-primary rounded-full"></span>}
          </Link>
        </nav>
      </div>

      {/* Footer Profile */}
      <div className="pt-space-md border-t border-outline-variant flex flex-col gap-1">
        <div 
          onClick={logout}
          className="flex items-center justify-between px-space-xs py-space-xs rounded-lg hover:bg-surface-container-low cursor-pointer transition-colors"
        >
          <div className="flex items-center gap-space-sm">
            <div className="w-8 h-8 rounded-full bg-surface-container-high border border-outline-variant flex items-center justify-center overflow-hidden">
              <span className="material-symbols-outlined text-primary">account_circle</span>
            </div>
            <div className="flex flex-col text-left overflow-hidden">
              <span className="font-label-md text-label-md font-semibold text-on-surface leading-tight">Sair</span>
              <span className="font-label-sm text-label-sm text-outline truncate w-28">{user?.email || 'Usuário'}</span>
            </div>
          </div>
          <span className="material-symbols-outlined text-outline text-lg">logout</span>
        </div>
      </div>
    </aside>
  );
}

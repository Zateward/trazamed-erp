'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { isAuthenticated, getUserRole, clearAuth } from '@/lib/auth';
import {
  LayoutDashboard, Pill, Wrench, Stethoscope,
  Brain, LogOut, Menu, X, ChevronRight, Hospital
} from 'lucide-react';
import { useState } from 'react';
import clsx from 'clsx';

const navItems = [
  { href: '/dashboard', label: 'Panel Principal', icon: LayoutDashboard, roles: [] },
  { href: '/dashboard/pharmacy', label: 'Farmacia', icon: Pill, roles: ['admin', 'pharmacist'] },
  { href: '/dashboard/ceye', label: 'CEyE', icon: Wrench, roles: ['admin', 'sterilization_tech'] },
  { href: '/dashboard/or', label: 'Quirófano', icon: Stethoscope, roles: ['admin', 'surgeon', 'nurse'] },
  { href: '/dashboard/ai', label: 'Asistente IA', icon: Brain, roles: [] },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login');
    }
  }, [router]);

  const handleLogout = () => {
    clearAuth();
    router.push('/login');
  };

  const role = getUserRole() || '';

  const visibleNavItems = navItems.filter(
    (item) => item.roles.length === 0 || item.roles.includes(role)
  );

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-primary-800">
        <div className="bg-white/10 rounded-lg p-2">
          <Hospital size={24} className="text-white" />
        </div>
        <div>
          <h1 className="text-white font-bold text-lg leading-tight">Hospitraze</h1>
          <p className="text-primary-300 text-xs">ERP Hospitalario</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {visibleNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setSidebarOpen(false)}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors duration-150 text-sm font-medium',
                isActive
                  ? 'bg-white/15 text-white'
                  : 'text-primary-200 hover:bg-white/10 hover:text-white'
              )}
            >
              <Icon size={18} />
              {item.label}
              {isActive && <ChevronRight size={14} className="ml-auto" />}
            </Link>
          );
        })}
      </nav>

      {/* Logout */}
      <div className="px-3 py-4 border-t border-primary-800">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-primary-200 hover:bg-white/10 hover:text-white transition-colors w-full text-sm font-medium"
        >
          <LogOut size={18} />
          Cerrar Sesión
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex flex-col w-64 bg-primary-900 flex-shrink-0">
        <SidebarContent />
      </aside>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setSidebarOpen(false)}
          />
          <aside className="absolute left-0 top-0 bottom-0 w-64 bg-primary-900 z-50">
            <SidebarContent />
          </aside>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mobile Header */}
        <header className="lg:hidden flex items-center gap-4 px-4 py-3 bg-white border-b border-gray-200">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-gray-100"
          >
            <Menu size={20} />
          </button>
          <span className="font-semibold text-gray-900">Hospitraze ERP</span>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

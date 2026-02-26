'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  Pill, Wrench, Stethoscope, Thermometer,
  AlertTriangle, CheckCircle, Clock, TrendingUp
} from 'lucide-react';

interface StatCard {
  title: string;
  value: string | number;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  color: string;
  subtitle?: string;
}

export default function DashboardPage() {
  const { data: products } = useQuery({
    queryKey: ['products'],
    queryFn: () => api.get('/api/v1/pharmacy/products?limit=500').then(r => r.data),
  });

  const { data: inventory } = useQuery({
    queryKey: ['inventory'],
    queryFn: () => api.get('/api/v1/pharmacy/inventory?limit=500').then(r => r.data),
  });

  const { data: cycles } = useQuery({
    queryKey: ['cycles'],
    queryFn: () => api.get('/api/v1/ceye/cycles?limit=100').then(r => r.data),
  });

  const { data: surgeries } = useQuery({
    queryKey: ['surgeries'],
    queryFn: () => api.get('/api/v1/or/surgeries?limit=100').then(r => r.data),
  });

  const totalProducts = products?.length ?? 0;
  const totalItems = inventory?.length ?? 0;
  const activeCycles = cycles?.filter((c: any) => c.status === 'in_progress').length ?? 0;
  const todaySurgeries = surgeries?.filter((s: any) => s.status !== 'cancelled').length ?? 0;

  const stats: StatCard[] = [
    {
      title: 'Productos Registrados',
      value: totalProducts,
      icon: Pill,
      color: 'bg-blue-500',
      subtitle: 'Catálogo GS1',
    },
    {
      title: 'Artículos en Inventario',
      value: totalItems,
      icon: TrendingUp,
      color: 'bg-green-500',
      subtitle: 'Lotes activos',
    },
    {
      title: 'Ciclos CEyE Activos',
      value: activeCycles,
      icon: Wrench,
      color: 'bg-amber-500',
      subtitle: 'En esterilización',
    },
    {
      title: 'Cirugías',
      value: todaySurgeries,
      icon: Stethoscope,
      color: 'bg-purple-500',
      subtitle: 'Registradas',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Panel Principal</h1>
        <p className="text-gray-500 text-sm mt-1">
          Bienvenido a Hospitraze ERP · Trazabilidad Hospitalaria
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.title} className="card flex items-center gap-4">
              <div className={`${stat.color} text-white rounded-xl p-3 flex-shrink-0`}>
                <Icon size={22} />
              </div>
              <div className="min-w-0">
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                <p className="text-sm font-medium text-gray-700 truncate">{stat.title}</p>
                {stat.subtitle && (
                  <p className="text-xs text-gray-400">{stat.subtitle}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Module Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ModuleCard
          title="Farmacia"
          description="Gestión de inventario farmacéutico con trazabilidad GS1 DataMatrix, cadena de frío y unidosis."
          icon={Pill}
          href="/dashboard/pharmacy"
          color="blue"
          features={['Escaneo GS1', 'Cadena de frío IoT', 'Unidosis']}
        />
        <ModuleCard
          title="CEyE"
          description="Control de ciclos de esterilización con autoclave, indicadores biológicos y rastreo RFID."
          icon={Wrench}
          href="/dashboard/ceye"
          color="amber"
          features={['Ciclos Autoclave', 'RFID Instrumentos', 'Indicadores']}
        />
        <ModuleCard
          title="Quirófano"
          description="Registro trans-operatorio: sets quirúrgicos, medicamentos y trazabilidad por paciente y cirujano."
          icon={Stethoscope}
          href="/dashboard/or"
          color="purple"
          features={['Registro trans-op', 'Sets quirúrgicos', 'Deducción inventario']}
        />
      </div>

      {/* Compliance Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-start gap-3">
        <CheckCircle size={20} className="text-blue-600 mt-0.5 flex-shrink-0" />
        <div>
          <p className="text-sm font-semibold text-blue-900">
            Sistema Certificado NOM-024-SSA3-2012 y NOM-241-SSA1-2025
          </p>
          <p className="text-xs text-blue-700 mt-0.5">
            Firma Electrónica Avanzada activada · Pista de auditoría inmutable ·
            RBAC aplicado · Retención de datos: 10 años
          </p>
        </div>
      </div>
    </div>
  );
}

function ModuleCard({
  title, description, icon: Icon, href, color, features
}: {
  title: string;
  description: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  href: string;
  color: 'blue' | 'amber' | 'purple';
  features: string[];
}) {
  const colorMap = {
    blue: { bg: 'bg-blue-100', text: 'text-blue-600', dot: 'bg-blue-500' },
    amber: { bg: 'bg-amber-100', text: 'text-amber-600', dot: 'bg-amber-500' },
    purple: { bg: 'bg-purple-100', text: 'text-purple-600', dot: 'bg-purple-500' },
  };
  const c = colorMap[color];

  return (
    <a href={href} className="card hover:shadow-md transition-shadow group">
      <div className={`inline-flex p-3 rounded-xl ${c.bg} mb-4`}>
        <Icon size={24} className={c.text} />
      </div>
      <h3 className="font-semibold text-gray-900 group-hover:text-primary-600 transition-colors">
        {title}
      </h3>
      <p className="text-sm text-gray-500 mt-2 leading-relaxed">{description}</p>
      <ul className="mt-3 space-y-1">
        {features.map((f) => (
          <li key={f} className="flex items-center gap-2 text-xs text-gray-600">
            <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
            {f}
          </li>
        ))}
      </ul>
    </a>
  );
}

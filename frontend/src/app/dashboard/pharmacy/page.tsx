'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';
import {
  Pill, ScanLine, Plus, Thermometer, AlertTriangle,
  Package, ChevronDown, Search, RefreshCw
} from 'lucide-react';
import clsx from 'clsx';

type TabType = 'inventory' | 'scan' | 'temperature' | 'products';

export default function PharmacyPage() {
  const [activeTab, setActiveTab] = useState<TabType>('inventory');

  const tabs = [
    { id: 'inventory' as TabType, label: 'Inventario', icon: Package },
    { id: 'scan' as TabType, label: 'Escanear GS1', icon: ScanLine },
    { id: 'temperature' as TabType, label: 'Cadena de Frío', icon: Thermometer },
    { id: 'products' as TabType, label: 'Productos', icon: Pill },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Pill className="text-blue-600" size={26} />
          Módulo de Farmacia
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          Gestión de inventario farmacéutico con trazabilidad GS1 DataMatrix
        </p>
      </div>

      {/* Tabs */}
      <div className="flex overflow-x-auto border-b border-gray-200 -mx-1">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={clsx(
              'flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors',
              activeTab === id
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            )}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'inventory' && <InventoryTab />}
      {activeTab === 'scan' && <ScanTab />}
      {activeTab === 'temperature' && <TemperatureTab />}
      {activeTab === 'products' && <ProductsTab />}
    </div>
  );
}

// -----------------------------------------------------------------------
// Inventory Tab
// -----------------------------------------------------------------------
function InventoryTab() {
  const [search, setSearch] = useState('');
  const { data: items = [], isLoading, refetch } = useQuery({
    queryKey: ['inventory'],
    queryFn: () => api.get('/api/v1/pharmacy/inventory').then(r => r.data),
  });

  const filtered = items.filter((item: any) =>
    item.product_name?.toLowerCase().includes(search.toLowerCase()) ||
    item.batch_number?.toLowerCase().includes(search.toLowerCase()) ||
    item.serial_number?.toLowerCase().includes(search.toLowerCase())
  );

  const isExpiringSoon = (expiry: string) => {
    const diff = new Date(expiry).getTime() - Date.now();
    return diff < 90 * 24 * 60 * 60 * 1000; // 90 days
  };

  const isExpired = (expiry: string) => new Date(expiry) < new Date();

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="input-field pl-9"
            placeholder="Buscar por nombre, lote o serie..."
          />
        </div>
        <button onClick={() => refetch()} className="btn-secondary flex items-center gap-2">
          <RefreshCw size={14} />
          Actualizar
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Cargando inventario...</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left px-4 py-3 font-medium text-gray-600">Producto</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Lote</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Serie</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Caducidad</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Cantidad</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-gray-400">
                    No hay artículos en inventario
                  </td>
                </tr>
              ) : (
                filtered.map((item: any) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{item.product_name || `Producto #${item.product_id}`}</td>
                    <td className="px-4 py-3 text-gray-600 font-mono text-xs">{item.batch_number}</td>
                    <td className="px-4 py-3 text-gray-500 font-mono text-xs">{item.serial_number || '—'}</td>
                    <td className="px-4 py-3 text-gray-600">
                      {new Date(item.expiry_date).toLocaleDateString('es-MX')}
                    </td>
                    <td className="px-4 py-3 text-right font-semibold">{Number(item.quantity).toLocaleString()}</td>
                    <td className="px-4 py-3">
                      {isExpired(item.expiry_date) ? (
                        <span className="badge-danger">Caducado</span>
                      ) : isExpiringSoon(item.expiry_date) ? (
                        <span className="badge-warning">Por vencer</span>
                      ) : (
                        <span className="badge-success">Vigente</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// -----------------------------------------------------------------------
// GS1 Scan Tab
// -----------------------------------------------------------------------
function ScanTab() {
  const queryClient = useQueryClient();
  const [rawScan, setRawScan] = useState('');
  const [locationId, setLocationId] = useState('1');
  const [lastResult, setLastResult] = useState<any>(null);

  const { data: locations = [] } = useQuery({
    queryKey: ['locations'],
    queryFn: () => api.get('/api/v1/pharmacy/locations').then(r => r.data),
  });

  const scanMutation = useMutation({
    mutationFn: (data: { raw_datamatrix: string; location_id: number }) =>
      api.post('/api/v1/pharmacy/scan', data).then(r => r.data),
    onSuccess: (data) => {
      setLastResult(data);
      toast.success('Artículo escaneado y registrado exitosamente');
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      setRawScan('');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Error al procesar el escaneo');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawScan.trim()) return;
    scanMutation.mutate({
      raw_datamatrix: rawScan.trim(),
      location_id: Number(locationId),
    });
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div className="card">
        <h3 className="font-semibold text-gray-900 mb-1 flex items-center gap-2">
          <ScanLine size={18} className="text-blue-600" />
          Escanear GS1 DataMatrix
        </h3>
        <p className="text-xs text-gray-500 mb-4">
          Conecte un lector GS1 o ingrese manualmente el código DataMatrix
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Código GS1 DataMatrix
            </label>
            <textarea
              value={rawScan}
              onChange={e => setRawScan(e.target.value)}
              className="input-field font-mono text-xs h-20 resize-none"
              placeholder="0107501234567890&#x1d;17260331&#x1d;10LOT123&#x1d;21SER456"
              autoFocus
            />
            <p className="text-xs text-gray-400 mt-1">
              Formato: GTIN(01) + Caducidad(17) + Lote(10) + Serie(21)
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Ubicación de destino
            </label>
            <select
              value={locationId}
              onChange={e => setLocationId(e.target.value)}
              className="input-field"
            >
              <option value="">Seleccionar ubicación...</option>
              {locations.map((loc: any) => (
                <option key={loc.id} value={loc.id}>
                  {loc.name} ({loc.code})
                </option>
              ))}
            </select>
          </div>

          <button
            type="submit"
            disabled={scanMutation.isPending || !rawScan.trim()}
            className="btn-primary flex items-center gap-2"
          >
            {scanMutation.isPending ? (
              <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
            ) : <ScanLine size={16} />}
            {scanMutation.isPending ? 'Procesando...' : 'Registrar Escaneo'}
          </button>
        </form>
      </div>

      {lastResult && (
        <div className="card border-l-4 border-green-500">
          <h4 className="font-semibold text-green-800 flex items-center gap-2 mb-3">
            <Package size={16} />
            Artículo Registrado
          </h4>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <dt className="text-gray-500">Producto ID:</dt>
            <dd className="font-mono">{lastResult.product_id}</dd>
            <dt className="text-gray-500">Lote:</dt>
            <dd className="font-mono">{lastResult.batch_number}</dd>
            <dt className="text-gray-500">Serie:</dt>
            <dd className="font-mono">{lastResult.serial_number || '—'}</dd>
            <dt className="text-gray-500">Cantidad:</dt>
            <dd className="font-semibold">{lastResult.quantity}</dd>
            <dt className="text-gray-500">Caducidad:</dt>
            <dd>{new Date(lastResult.expiry_date).toLocaleDateString('es-MX')}</dd>
          </dl>
        </div>
      )}
    </div>
  );
}

// -----------------------------------------------------------------------
// Temperature Tab
// -----------------------------------------------------------------------
function TemperatureTab() {
  const queryClient = useQueryClient();
  const [selectedLocation, setSelectedLocation] = useState('');
  const [tempValue, setTempValue] = useState('');
  const [sensorId, setSensorId] = useState('SENSOR-001');

  const { data: locations = [] } = useQuery({
    queryKey: ['locations'],
    queryFn: () => api.get('/api/v1/pharmacy/locations').then(r => r.data),
  });

  const { data: tempHistory = [] } = useQuery({
    queryKey: ['temperature', selectedLocation],
    queryFn: () =>
      selectedLocation
        ? api.get(`/api/v1/pharmacy/temperature/${selectedLocation}`).then(r => r.data)
        : [],
    enabled: !!selectedLocation,
  });

  const logMutation = useMutation({
    mutationFn: (data: any) => api.post('/api/v1/pharmacy/temperature', data).then(r => r.data),
    onSuccess: (data) => {
      if (data.is_alert) {
        toast.error(`⚠️ ALERTA: Temperatura fuera de rango: ${data.temperature_c}°C`);
      } else {
        toast.success(`Temperatura registrada: ${data.temperature_c}°C`);
      }
      queryClient.invalidateQueries({ queryKey: ['temperature', selectedLocation] });
      setTempValue('');
    },
  });

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Log form */}
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Thermometer size={18} className="text-blue-600" />
            Registrar Temperatura
          </h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Ubicación</label>
              <select
                value={selectedLocation}
                onChange={e => setSelectedLocation(e.target.value)}
                className="input-field"
              >
                <option value="">Seleccionar...</option>
                {locations.map((loc: any) => (
                  <option key={loc.id} value={loc.id}>{loc.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sensor ID</label>
              <input value={sensorId} onChange={e => setSensorId(e.target.value)} className="input-field" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Temperatura (°C)</label>
              <input
                type="number"
                step="0.1"
                value={tempValue}
                onChange={e => setTempValue(e.target.value)}
                className="input-field"
                placeholder="Ej: 5.2"
              />
            </div>
            <button
              className="btn-primary w-full"
              disabled={!selectedLocation || !tempValue || logMutation.isPending}
              onClick={() =>
                logMutation.mutate({
                  location_id: Number(selectedLocation),
                  sensor_id: sensorId,
                  temperature_c: Number(tempValue),
                })
              }
            >
              Registrar
            </button>
          </div>
        </div>

        {/* History */}
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-4">Historial de Temperatura</h3>
          {tempHistory.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-6">
              Seleccione una ubicación para ver el historial
            </p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {tempHistory.map((log: any) => (
                <div
                  key={log.id}
                  className={clsx(
                    'flex items-center justify-between p-2 rounded-lg text-sm',
                    log.is_alert ? 'bg-red-50 border border-red-200' : 'bg-gray-50'
                  )}
                >
                  <div className="flex items-center gap-2">
                    {log.is_alert && <AlertTriangle size={14} className="text-red-500" />}
                    <span className="font-semibold">{log.temperature_c}°C</span>
                    <span className="text-gray-400 text-xs">{log.sensor_id}</span>
                  </div>
                  <span className="text-gray-400 text-xs">
                    {new Date(log.recorded_at).toLocaleTimeString('es-MX')}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------
// Products Tab
// -----------------------------------------------------------------------
function ProductsTab() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const { data: products = [], isLoading } = useQuery({
    queryKey: ['products'],
    queryFn: () => api.get('/api/v1/pharmacy/products').then(r => r.data),
  });

  const [form, setForm] = useState({
    gtin: '', name: '', generic_name: '', manufacturer: '',
    pharmaceutical_form: '', concentration: '',
    requires_cold_chain: false, controlled_substance: false,
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/api/v1/pharmacy/products', data).then(r => r.data),
    onSuccess: () => {
      toast.success('Producto registrado');
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setShowForm(false);
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Error'),
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button className="btn-primary flex items-center gap-2" onClick={() => setShowForm(!showForm)}>
          <Plus size={16} />
          Nuevo Producto
        </button>
      </div>

      {showForm && (
        <div className="card">
          <h3 className="font-semibold mb-4">Registrar Producto GS1</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { name: 'gtin', label: 'GTIN (14 dígitos)' },
              { name: 'name', label: 'Nombre comercial' },
              { name: 'generic_name', label: 'Nombre genérico' },
              { name: 'manufacturer', label: 'Fabricante' },
              { name: 'pharmaceutical_form', label: 'Forma farmacéutica' },
              { name: 'concentration', label: 'Concentración' },
            ].map(({ name, label }) => (
              <div key={name}>
                <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                <input
                  className="input-field"
                  value={(form as any)[name]}
                  onChange={e => setForm({ ...form, [name]: e.target.value })}
                />
              </div>
            ))}
            <div className="flex items-center gap-4 sm:col-span-2">
              {[
                { name: 'requires_cold_chain', label: 'Requiere cadena de frío' },
                { name: 'controlled_substance', label: 'Sustancia controlada' },
              ].map(({ name, label }) => (
                <label key={name} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={(form as any)[name]}
                    onChange={e => setForm({ ...form, [name]: e.target.checked })}
                    className="rounded"
                  />
                  {label}
                </label>
              ))}
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button
              className="btn-primary"
              onClick={() => createMutation.mutate(form)}
              disabled={createMutation.isPending || !form.gtin || !form.name}
            >
              Guardar
            </button>
            <button className="btn-secondary" onClick={() => setShowForm(false)}>Cancelar</button>
          </div>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left px-4 py-3 font-medium text-gray-600">GTIN</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Nombre</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Fabricante</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Forma</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Atributos</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={5} className="text-center py-8 text-gray-400">Cargando...</td></tr>
            ) : products.length === 0 ? (
              <tr><td colSpan={5} className="text-center py-8 text-gray-400">Sin productos registrados</td></tr>
            ) : products.map((p: any) => (
              <tr key={p.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{p.gtin}</td>
                <td className="px-4 py-3 font-medium">{p.name}</td>
                <td className="px-4 py-3 text-gray-500">{p.manufacturer || '—'}</td>
                <td className="px-4 py-3 text-gray-500">{p.pharmaceutical_form || '—'}</td>
                <td className="px-4 py-3">
                  <div className="flex gap-1 flex-wrap">
                    {p.requires_cold_chain && <span className="badge-info">❄️ Frío</span>}
                    {p.controlled_substance && <span className="badge-warning">⚠️ Controlado</span>}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

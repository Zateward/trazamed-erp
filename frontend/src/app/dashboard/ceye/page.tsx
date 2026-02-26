'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';
import { Wrench, Plus, ChevronRight, CheckCircle, XCircle, Clock } from 'lucide-react';
import clsx from 'clsx';

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pendiente',
  in_progress: 'En Proceso',
  completed: 'Completado',
  failed: 'Fallido',
  quarantine: 'Cuarentena',
};

const STATUS_CLASSES: Record<string, string> = {
  pending: 'badge-info',
  in_progress: 'badge-warning',
  completed: 'badge-success',
  failed: 'badge-danger',
  quarantine: 'badge-danger',
};

const STAGES = ['washing', 'inspection', 'packaging', 'sterilization', 'delivery'];
const STAGE_LABELS: Record<string, string> = {
  washing: 'Lavado',
  inspection: 'Inspección',
  packaging: 'Empaque',
  sterilization: 'Esterilización',
  delivery: 'Entrega',
};

export default function CEyEPage() {
  const queryClient = useQueryClient();
  const [showNewForm, setShowNewForm] = useState(false);
  const [selectedCycle, setSelectedCycle] = useState<any>(null);
  const [form, setForm] = useState({
    autoclave_id: '', cycle_number: '',
    temperature_c: '134', pressure_kpa: '206', duration_minutes: '18',
  });
  const [stageForm, setStageForm] = useState({
    stage: 'washing',
    biological_indicator_result: '',
    chemical_indicator_result: '',
  });

  const { data: cycles = [], isLoading } = useQuery({
    queryKey: ['cycles'],
    queryFn: () => api.get('/api/v1/ceye/cycles?limit=50').then(r => r.data),
  });

  const { data: instruments = [] } = useQuery({
    queryKey: ['instruments'],
    queryFn: () => api.get('/api/v1/ceye/instruments').then(r => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/api/v1/ceye/cycles', data).then(r => r.data),
    onSuccess: () => {
      toast.success('Ciclo de esterilización iniciado');
      queryClient.invalidateQueries({ queryKey: ['cycles'] });
      setShowNewForm(false);
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Error'),
  });

  const advanceMutation = useMutation({
    mutationFn: ({ cycleId, data }: { cycleId: number; data: any }) =>
      api.patch(`/api/v1/ceye/cycles/${cycleId}/advance`, data).then(r => r.data),
    onSuccess: (data) => {
      toast.success(`Etapa "${STAGE_LABELS[stageForm.stage]}" completada`);
      queryClient.invalidateQueries({ queryKey: ['cycles'] });
      setSelectedCycle(data);
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Error'),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Wrench className="text-amber-600" size={26} />
            CEyE - Central de Esterilización
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            Ciclos de esterilización: Lavado → Inspección → Empaque → Esterilización → Entrega
          </p>
        </div>
        <button
          className="btn-primary flex items-center gap-2"
          onClick={() => setShowNewForm(true)}
        >
          <Plus size={16} />
          Nuevo Ciclo
        </button>
      </div>

      {/* New Cycle Form */}
      {showNewForm && (
        <div className="card">
          <h3 className="font-semibold mb-4">Registrar Nuevo Ciclo de Esterilización</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { name: 'autoclave_id', label: 'ID Autoclave', placeholder: 'AUT-01' },
              { name: 'cycle_number', label: 'Número de ciclo', placeholder: 'C2024-001' },
              { name: 'temperature_c', label: 'Temperatura (°C)', placeholder: '134' },
              { name: 'pressure_kpa', label: 'Presión (kPa)', placeholder: '206' },
              { name: 'duration_minutes', label: 'Duración (min)', placeholder: '18' },
            ].map(({ name, label, placeholder }) => (
              <div key={name}>
                <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                <input
                  className="input-field"
                  value={(form as any)[name]}
                  placeholder={placeholder}
                  onChange={e => setForm({ ...form, [name]: e.target.value })}
                />
              </div>
            ))}
          </div>
          <div className="flex gap-3 mt-4">
            <button
              className="btn-primary"
              disabled={createMutation.isPending || !form.autoclave_id || !form.cycle_number}
              onClick={() =>
                createMutation.mutate({
                  ...form,
                  temperature_c: Number(form.temperature_c),
                  pressure_kpa: Number(form.pressure_kpa),
                  duration_minutes: Number(form.duration_minutes),
                  instrument_ids: [],
                })
              }
            >
              Iniciar Ciclo
            </button>
            <button className="btn-secondary" onClick={() => setShowNewForm(false)}>Cancelar</button>
          </div>
        </div>
      )}

      {/* Cycles Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left px-4 py-3 font-medium text-gray-600">Autoclave</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Ciclo</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Estado</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Temp / Presión</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Indicadores</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Fecha</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={7} className="text-center py-8 text-gray-400">Cargando...</td></tr>
            ) : cycles.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-8 text-gray-400">Sin ciclos registrados</td></tr>
            ) : cycles.map((cycle: any) => (
              <tr key={cycle.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{cycle.autoclave_id}</td>
                <td className="px-4 py-3 font-mono text-xs">{cycle.cycle_number}</td>
                <td className="px-4 py-3">
                  <span className={STATUS_CLASSES[cycle.status] || 'badge-info'}>
                    {STATUS_LABELS[cycle.status] || cycle.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {cycle.temperature_c ? `${cycle.temperature_c}°C / ${cycle.pressure_kpa}kPa` : '—'}
                </td>
                <td className="px-4 py-3">
                  {cycle.biological_indicator_result ? (
                    <span className={cycle.biological_indicator_result === 'pass' ? 'text-green-600' : 'text-red-600'}>
                      BIO: {cycle.biological_indicator_result}
                    </span>
                  ) : '—'}
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {new Date(cycle.created_at).toLocaleDateString('es-MX')}
                </td>
                <td className="px-4 py-3">
                  {cycle.status !== 'completed' && cycle.status !== 'failed' && (
                    <button
                      className="text-primary-600 hover:text-primary-700 text-xs font-medium"
                      onClick={() => setSelectedCycle(cycle)}
                    >
                      Avanzar →
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Advance Stage Modal */}
      {selectedCycle && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h3 className="font-bold text-lg mb-2">Avanzar Ciclo: {selectedCycle.cycle_number}</h3>
            <p className="text-sm text-gray-500 mb-4">Autoclave: {selectedCycle.autoclave_id}</p>

            {/* Stage indicator */}
            <div className="flex items-center gap-1 mb-4 overflow-x-auto pb-1">
              {STAGES.map((s, i) => {
                const completed =
                  (s === 'washing' && selectedCycle.washing_completed_at) ||
                  (s === 'inspection' && selectedCycle.inspection_completed_at) ||
                  (s === 'packaging' && selectedCycle.packaging_completed_at) ||
                  (s === 'sterilization' && selectedCycle.sterilization_completed_at) ||
                  (s === 'delivery' && selectedCycle.delivered_at);
                return (
                  <div key={s} className="flex items-center gap-1 text-xs">
                    {i > 0 && <ChevronRight size={12} className="text-gray-300 flex-shrink-0" />}
                    <span className={clsx(
                      'px-2 py-1 rounded whitespace-nowrap',
                      completed ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                    )}>
                      {STAGE_LABELS[s]}
                    </span>
                  </div>
                );
              })}
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Etapa a completar</label>
                <select
                  value={stageForm.stage}
                  onChange={e => setStageForm({ ...stageForm, stage: e.target.value })}
                  className="input-field"
                >
                  {STAGES.map(s => (
                    <option key={s} value={s}>{STAGE_LABELS[s]}</option>
                  ))}
                </select>
              </div>

              {stageForm.stage === 'sterilization' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Indicador biológico
                    </label>
                    <select
                      value={stageForm.biological_indicator_result}
                      onChange={e => setStageForm({ ...stageForm, biological_indicator_result: e.target.value })}
                      className="input-field"
                    >
                      <option value="">Pendiente</option>
                      <option value="pass">✅ Pasa</option>
                      <option value="fail">❌ Falla</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Indicador químico
                    </label>
                    <select
                      value={stageForm.chemical_indicator_result}
                      onChange={e => setStageForm({ ...stageForm, chemical_indicator_result: e.target.value })}
                      className="input-field"
                    >
                      <option value="">Pendiente</option>
                      <option value="pass">✅ Pasa</option>
                      <option value="fail">❌ Falla</option>
                    </select>
                  </div>
                </>
              )}
            </div>

            <div className="flex gap-3 mt-5">
              <button
                className="btn-primary flex-1"
                disabled={advanceMutation.isPending}
                onClick={() => advanceMutation.mutate({
                  cycleId: selectedCycle.id,
                  data: stageForm,
                })}
              >
                Completar Etapa
              </button>
              <button className="btn-secondary" onClick={() => setSelectedCycle(null)}>
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

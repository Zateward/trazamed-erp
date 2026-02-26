'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';
import { Stethoscope, Plus, Play, CheckCircle } from 'lucide-react';

const STATUS_MAP: Record<string, { label: string; cls: string }> = {
  scheduled: { label: 'Programada', cls: 'badge-info' },
  in_progress: { label: 'En Curso', cls: 'badge-warning' },
  completed: { label: 'Completada', cls: 'badge-success' },
  cancelled: { label: 'Cancelada', cls: 'badge-danger' },
};

export default function ORPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    surgery_code: '', patient_id: '',
    surgeon_id: '', procedure_name: '',
    operating_room: '', diagnosis_code: '',
  });

  const { data: surgeries = [], isLoading } = useQuery({
    queryKey: ['surgeries'],
    queryFn: () => api.get('/api/v1/or/surgeries?limit=50').then(r => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/api/v1/or/surgeries', data).then(r => r.data),
    onSuccess: () => {
      toast.success('Cirugía registrada exitosamente');
      queryClient.invalidateQueries({ queryKey: ['surgeries'] });
      setShowForm(false);
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Error'),
  });

  const startMutation = useMutation({
    mutationFn: (id: number) => api.patch(`/api/v1/or/surgeries/${id}/start`).then(r => r.data),
    onSuccess: () => {
      toast.success('Cirugía iniciada');
      queryClient.invalidateQueries({ queryKey: ['surgeries'] });
    },
  });

  const completeMutation = useMutation({
    mutationFn: (id: number) => api.patch(`/api/v1/or/surgeries/${id}/complete`).then(r => r.data),
    onSuccess: () => {
      toast.success('Cirugía completada y firmada digitalmente');
      queryClient.invalidateQueries({ queryKey: ['surgeries'] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Stethoscope className="text-purple-600" size={26} />
            Quirófano - Registro Trans-operatorio
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            Registro de cirugías con trazabilidad de sets, medicamentos y firma FEA
          </p>
        </div>
        <button className="btn-primary flex items-center gap-2" onClick={() => setShowForm(true)}>
          <Plus size={16} />
          Nueva Cirugía
        </button>
      </div>

      {showForm && (
        <div className="card">
          <h3 className="font-semibold mb-4">Registrar Nueva Cirugía</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { name: 'surgery_code', label: 'Código de cirugía', placeholder: 'QX-2024-001' },
              { name: 'patient_id', label: 'ID de paciente (pseudonimizado)', placeholder: 'PAT-XXXXX' },
              { name: 'surgeon_id', label: 'ID del cirujano', placeholder: '1' },
              { name: 'procedure_name', label: 'Nombre del procedimiento' },
              { name: 'operating_room', label: 'Quirófano', placeholder: 'QX-01' },
              { name: 'diagnosis_code', label: 'Código CIE-10', placeholder: 'K80.20' },
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
              disabled={createMutation.isPending || !form.surgery_code || !form.patient_id}
              onClick={() => createMutation.mutate({
                ...form,
                surgeon_id: Number(form.surgeon_id),
                surgical_set_ids: [],
              })}
            >
              Registrar
            </button>
            <button className="btn-secondary" onClick={() => setShowForm(false)}>Cancelar</button>
          </div>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left px-4 py-3 font-medium text-gray-600">Código</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Procedimiento</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Paciente</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Quirófano</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Estado</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">FEA</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={7} className="text-center py-8 text-gray-400">Cargando...</td></tr>
            ) : surgeries.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-8 text-gray-400">Sin cirugías registradas</td></tr>
            ) : surgeries.map((s: any) => {
              const { label, cls } = STATUS_MAP[s.status] || { label: s.status, cls: 'badge-info' };
              return (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{s.surgery_code}</td>
                  <td className="px-4 py-3 font-medium">{s.procedure_name}</td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">{s.patient_id}</td>
                  <td className="px-4 py-3 text-gray-500">{s.operating_room || '—'}</td>
                  <td className="px-4 py-3">
                    <span className={cls}>{label}</span>
                  </td>
                  <td className="px-4 py-3">
                    {s.signature ? (
                      <span className="text-green-600 text-xs flex items-center gap-1">
                        <CheckCircle size={12} /> Firmado
                      </span>
                    ) : (
                      <span className="text-gray-400 text-xs">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      {s.status === 'scheduled' && (
                        <button
                          className="text-xs text-amber-600 hover:text-amber-700 font-medium flex items-center gap-1"
                          onClick={() => startMutation.mutate(s.id)}
                        >
                          <Play size={12} /> Iniciar
                        </button>
                      )}
                      {s.status === 'in_progress' && (
                        <button
                          className="text-xs text-green-600 hover:text-green-700 font-medium flex items-center gap-1"
                          onClick={() => completeMutation.mutate(s.id)}
                        >
                          <CheckCircle size={12} /> Completar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

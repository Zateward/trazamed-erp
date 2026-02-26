'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';
import { Brain, Send, User, Loader2, Sparkles } from 'lucide-react';

const EXAMPLE_QUERIES = [
  '¿Cuál es nuestro stock actual de Propofol que vence en marzo?',
  'Lista todas las cirugías donde se usaron instrumentos del Autoclave #2 hoy.',
  '¿Qué medicamentos administrados vencen en los próximos 90 días?',
  'Resume el historial clínico del paciente PAT-123456.',
];

interface Message {
  role: 'user' | 'assistant';
  content: string;
  model?: string;
}

export default function AIPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [query, setQuery] = useState('');
  const [patientId, setPatientId] = useState('');
  const [showSummary, setShowSummary] = useState(false);

  const queryMutation = useMutation({
    mutationFn: (q: string) =>
      api.post('/api/v1/ai/query', { query: q, context_limit: 10 }).then(r => r.data),
    onSuccess: (data) => {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: data.answer, model: data.model_used },
      ]);
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Error en la consulta'),
  });

  const summaryMutation = useMutation({
    mutationFn: (pid: string) =>
      api.post('/api/v1/ai/clinical-summary', {
        patient_id: pid,
        include_medications: true,
        include_surgeries: true,
      }).then(r => r.data),
    onSuccess: (data) => {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `**Resumen Clínico — Paciente ${data.patient_id}:**\n\n${data.summary}`,
          model: 'clinical-summarizer',
        },
      ]);
      setShowSummary(false);
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Error'),
  });

  const handleSend = () => {
    if (!query.trim()) return;
    setMessages(prev => [...prev, { role: 'user', content: query }]);
    queryMutation.mutate(query);
    setQuery('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isLoading = queryMutation.isPending || summaryMutation.isPending;

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Brain className="text-violet-600" size={26} />
          Asistente IA Hospitraze
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          Motor RAG con Gemini 2.0 Flash · Consultas en lenguaje natural sobre datos hospitalarios
        </p>
      </div>

      {/* Chat Area */}
      <div className="card min-h-[400px] flex flex-col">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center py-8">
            <div className="bg-violet-100 rounded-full p-4 mb-4">
              <Brain size={32} className="text-violet-600" />
            </div>
            <p className="font-semibold text-gray-700 mb-2">Consultas en Lenguaje Natural</p>
            <p className="text-sm text-gray-500 text-center max-w-md mb-6">
              Pregunta sobre inventario, cirugías, esterilización o historiales clínicos.
              El asistente consulta los datos reales del hospital.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
              {EXAMPLE_QUERIES.map((q) => (
                <button
                  key={q}
                  onClick={() => {
                    setQuery(q);
                    setMessages(prev => [...prev, { role: 'user', content: q }]);
                    queryMutation.mutate(q);
                    setQuery('');
                  }}
                  className="text-left text-xs px-3 py-2 rounded-lg border border-gray-200 hover:border-violet-300 hover:bg-violet-50 text-gray-600 transition-colors"
                >
                  &ldquo;{q}&rdquo;
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex-1 space-y-4 overflow-y-auto max-h-96 pr-1">
            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  msg.role === 'user' ? 'bg-primary-600' : 'bg-violet-100'
                }`}>
                  {msg.role === 'user'
                    ? <User size={14} className="text-white" />
                    : <Brain size={14} className="text-violet-600" />
                  }
                </div>
                <div className={`max-w-[75%] rounded-xl px-4 py-3 text-sm ${
                  msg.role === 'user'
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.model && msg.role === 'assistant' && (
                    <p className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                      <Sparkles size={10} />
                      {msg.model}
                    </p>
                  )}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-violet-100 flex items-center justify-center">
                  <Loader2 size={14} className="text-violet-600 animate-spin" />
                </div>
                <div className="bg-gray-100 rounded-xl px-4 py-3 text-sm text-gray-400">
                  Analizando datos hospitalarios...
                </div>
              </div>
            )}
          </div>
        )}

        {/* Input */}
        <div className="mt-4 flex gap-2 border-t pt-4">
          <textarea
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            className="input-field flex-1 resize-none"
            placeholder="Pregunta sobre inventario, cirugías, esterilización..."
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !query.trim()}
            className="btn-primary px-4 self-end flex items-center gap-2"
          >
            {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            Enviar
          </button>
        </div>
      </div>

      {/* Clinical Summary Tool */}
      <div className="card">
        <h3 className="font-semibold mb-3 flex items-center gap-2">
          <User size={18} className="text-violet-600" />
          Resumen Clínico por Paciente
        </h3>
        <p className="text-sm text-gray-500 mb-4">
          Genera un resumen clínico basado en el historial de trazabilidad del paciente.
        </p>
        <div className="flex gap-3">
          <input
            value={patientId}
            onChange={e => setPatientId(e.target.value)}
            className="input-field flex-1"
            placeholder="ID del paciente (Ej: PAT-123456)"
          />
          <button
            className="btn-primary flex items-center gap-2"
            disabled={!patientId || summaryMutation.isPending}
            onClick={() => {
              setMessages(prev => [
                ...prev,
                { role: 'user', content: `Genera resumen clínico para: ${patientId}` },
              ]);
              summaryMutation.mutate(patientId);
            }}
          >
            <Brain size={16} />
            Generar
          </button>
        </div>
      </div>
    </div>
  );
}

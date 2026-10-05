'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, ConversaListResponse, Sentimento } from '@/lib/api';
import { AppLayout } from '@/components/AppLayout';
import Link from 'next/link';

type FilterType = 'TODAS' | 'NEGATIVAS' | 'POSITIVAS' | 'QUEDA' | 'PENDENTES';

export default function ConversasListPage() {
  const [filter, setFilter] = useState<FilterType>('TODAS');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['conversas'],
    queryFn: async () => {
      // Pedimos 500 para conseguirmos fazer o filtro decente no client-side
      const res = await api.get<ConversaListResponse>('/conversas?limite=500');
      return res.data;
    }
  });

  const getSentimentoBg = (sentimento: Sentimento | null) => {
    switch (sentimento) {
      case 'positivo': return 'bg-[#10b981]';
      case 'negativo': return 'bg-[#ef4444]';
      case 'neutro': return 'bg-[#64748b]';
      default: return 'bg-outline-variant';
    }
  };

  const conversasFiltradas = data?.conversas.filter(c => {
    if (filter === 'TODAS') return true;
    if (filter === 'PENDENTES') return c.indicadores === null;
    if (!c.indicadores) return false;

    if (filter === 'NEGATIVAS') return c.indicadores.encerramento === 'negativo';
    if (filter === 'POSITIVAS') return c.indicadores.encerramento === 'positivo';
    if (filter === 'QUEDA') return c.indicadores.delta < 0;
    
    return true;
  }) || [];

  return (
    <AppLayout title="Lista de Conversas" subtitle="Visão geral e filtragem avançada de todos os atendimentos importados.">
      
      {/* Barra de Filtros e KPIs */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-space-md shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4 mb-space-xl">
        <div className="flex flex-wrap items-center gap-2">
          <button 
            onClick={() => setFilter('TODAS')}
            className={`px-4 py-1.5 rounded-full font-label-sm text-sm font-semibold transition-colors ${filter === 'TODAS' ? 'bg-[#4f46e5] text-white' : 'bg-surface-container hover:bg-surface-container-high text-on-surface-variant'}`}
          >
            Todas
          </button>
          <button 
            onClick={() => setFilter('NEGATIVAS')}
            className={`px-4 py-1.5 rounded-full font-label-sm text-sm font-semibold transition-colors flex items-center gap-1 ${filter === 'NEGATIVAS' ? 'bg-[#fff1f2] border border-[#fecdd3] text-[#9f1239]' : 'bg-surface-container hover:bg-surface-container-high text-on-surface-variant'}`}
          >
            <span className={`w-2 h-2 rounded-full ${filter === 'NEGATIVAS' ? 'bg-[#ef4444]' : 'bg-outline'}`}></span>
            Finais Negativas
          </button>
          <button 
            onClick={() => setFilter('POSITIVAS')}
            className={`px-4 py-1.5 rounded-full font-label-sm text-sm font-semibold transition-colors flex items-center gap-1 ${filter === 'POSITIVAS' ? 'bg-[#ecfdf5] border border-[#a7f3d0] text-[#065f46]' : 'bg-surface-container hover:bg-surface-container-high text-on-surface-variant'}`}
          >
            <span className={`w-2 h-2 rounded-full ${filter === 'POSITIVAS' ? 'bg-[#10b981]' : 'bg-outline'}`}></span>
            Finais Positivas
          </button>
          <button 
            onClick={() => setFilter('QUEDA')}
            className={`px-4 py-1.5 rounded-full font-label-sm text-sm font-semibold transition-colors flex items-center gap-1 ${filter === 'QUEDA' ? 'bg-error text-on-error' : 'bg-surface-container hover:bg-surface-container-high text-on-surface-variant'}`}
          >
            <span className="material-symbols-outlined text-[16px]">trending_down</span>
            Houve Queda
          </button>
          <button 
            onClick={() => setFilter('PENDENTES')}
            className={`px-4 py-1.5 rounded-full font-label-sm text-sm font-semibold transition-colors flex items-center gap-1 ${filter === 'PENDENTES' ? 'bg-outline text-white' : 'bg-surface-container hover:bg-surface-container-high text-on-surface-variant'}`}
          >
            Não Classificadas
          </button>
        </div>
        
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-low border border-outline-variant">
          <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse"></span>
          <span className="font-mono font-bold text-on-surface">{conversasFiltradas.length}</span>
          <span className="font-body-sm text-sm text-outline">resultados</span>
        </div>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low/60 border-b border-outline-variant text-outline font-label-sm text-xs uppercase tracking-widest h-12">
                <th className="py-2.5 px-4 font-bold" scope="col">ID da Conversa</th>
                <th className="py-2.5 px-4 font-bold" scope="col">Canal (Fonte)</th>
                <th className="py-2.5 px-4 font-bold" scope="col">Evolução (Início → Fim)</th>
                <th className="py-2.5 px-4 font-bold text-center" scope="col">Mensagens</th>
                <th className="py-2.5 px-4 font-bold" scope="col">Status de Alerta</th>
                <th className="py-2.5 px-4 font-bold text-right" scope="col">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/30 font-body-sm text-sm">
              {isLoading ? (
                <tr><td colSpan={6} className="text-center py-12 text-outline">Carregando base de conversas...</td></tr>
              ) : isError ? (
                <tr><td colSpan={6} className="text-center py-12 text-error">Erro ao carregar lista de conversas do servidor.</td></tr>
              ) : conversasFiltradas.length === 0 ? (
                <tr><td colSpan={6} className="text-center py-12 text-on-surface-variant font-medium">Nenhuma conversa encontrada para os filtros selecionados.</td></tr>
              ) : (
                conversasFiltradas.map(conversa => {
                  const { indicadores } = conversa;
                  const isCritical = indicadores && indicadores.delta < 0;
                  const isRecovery = indicadores && indicadores.delta > 0;

                  return (
                    <tr key={conversa.id} className={`hover:bg-surface-container-low/80 transition-colors group ${isCritical ? 'bg-[#fff1f2]/30' : ''}`}>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-on-surface">#{conversa.origem_id}</span>
                          {isCritical && <span className="w-2 h-2 rounded-full bg-[#ef4444] animate-ping" title="Queda crítica"></span>}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold text-xs px-2 py-1 rounded bg-surface-container text-outline capitalize">{conversa.fonte}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {indicadores ? (
                          <div className="flex items-center gap-2">
                            <span className={`inline-flex items-center gap-1 font-bold text-xs uppercase px-2 py-0.5 rounded-full border ${indicadores.abertura === 'negativo' ? 'bg-[#fff1f2] text-[#9f1239] border-[#fecdd3]' : indicadores.abertura === 'positivo' ? 'bg-[#ecfdf5] text-[#065f46] border-[#a7f3d0]' : 'bg-surface-container text-on-surface-variant border-outline-variant'}`}>
                              <span className={`w-1.5 h-1.5 rounded-full ${getSentimentoBg(indicadores.abertura)}`}></span>
                              {indicadores.abertura}
                            </span>
                            <span className="material-symbols-outlined text-outline text-[16px]">arrow_forward</span>
                            <span className={`inline-flex items-center gap-1 font-bold text-xs uppercase px-2 py-0.5 rounded-full border ${indicadores.encerramento === 'negativo' ? 'bg-[#fff1f2] text-[#9f1239] border-[#fecdd3]' : indicadores.encerramento === 'positivo' ? 'bg-[#ecfdf5] text-[#065f46] border-[#a7f3d0]' : 'bg-surface-container text-on-surface-variant border-outline-variant'}`}>
                              <span className={`w-1.5 h-1.5 rounded-full ${getSentimentoBg(indicadores.encerramento)}`}></span>
                              {indicadores.encerramento}
                            </span>
                          </div>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-container text-outline text-xs font-semibold">
                            <span className="material-symbols-outlined text-[14px]">pending</span>
                            Pendente de Classificação
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center font-mono font-medium text-on-surface">
                        {indicadores ? indicadores.n_mensagens : '-'}
                      </td>
                      <td className="py-3 px-4">
                        {indicadores ? (
                          isCritical ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#ef4444] text-white font-label-sm text-xs font-bold shadow-sm">
                              <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span>
                              Atrito Detectado
                            </span>
                          ) : isRecovery ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#10b981] text-white font-label-sm text-xs font-bold shadow-sm">
                              <span className="w-1.5 h-1.5 rounded-full bg-white"></span>
                              Recuperação
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-surface-container-high text-on-surface-variant font-label-sm text-xs font-semibold">
                              Estável
                            </span>
                          )
                        ) : (
                          <span className="text-outline-variant">-</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Link 
                          href={`/conversas/${conversa.id}`}
                          className="inline-flex items-center justify-center h-8 px-3 rounded-lg border border-outline-variant bg-surface-container-lowest hover:border-[#4f46e5] hover:text-[#4f46e5] text-on-surface font-label-sm text-sm font-semibold transition-all shadow-sm group-hover:bg-[#eef2ff]"
                        >
                          Analisar
                        </Link>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppLayout>
  );
}

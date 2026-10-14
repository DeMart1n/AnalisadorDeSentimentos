'use client';

import { useQuery } from '@tanstack/react-query';
import { api, MetricasResponse, ConversaListResponse } from '@/lib/api';
import { AppLayout } from '@/components/AppLayout';
import Link from 'next/link';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend } from 'recharts';

export default function DashboardPage() {
  // 1. Buscar métricas agregadas (Dashboard)
  const { data: metricas, isLoading: loadingMetricas } = useQuery({
    queryKey: ['metricas'],
    queryFn: async () => {
      const res = await api.get<MetricasResponse>('/metricas');
      return res.data;
    }
  });

  // 2. Buscar conversas para montar a tabela de críticos
  const { data: conversasData, isLoading: loadingConversas } = useQuery({
    queryKey: ['conversas_criticas'],
    queryFn: async () => {
      const res = await api.get<ConversaListResponse>('/conversas?limite=500');
      return res.data;
    }
  });

  // =======================
  // PROCESSAMENTO DE DADOS
  // =======================
  
  // Distribuição geral
  const total = metricas?.total_conversas || 0;
  const dist = metricas?.distribuicao || { positivo: 0, negativo: 0, neutro: 0 };
  const classificados = dist.positivo + dist.negativo + dist.neutro;

  const pctPositivo = classificados ? ((dist.positivo / classificados) * 100).toFixed(1) : '0.0';
  const pctNegativo = classificados ? ((dist.negativo / classificados) * 100).toFixed(1) : '0.0';
  const pctNeutro = classificados ? ((dist.neutro / classificados) * 100).toFixed(1) : '0.0';

  const pieData = [
    { name: 'Positivo', value: dist.positivo, color: '#10b981' }, // emerald-500
    { name: 'Negativo', value: dist.negativo, color: '#ef4444' }, // rose-500
    { name: 'Neutro', value: dist.neutro, color: '#64748b' }      // slate-500
  ];

  // Modelos de IA
  const modelos = metricas?.modelos;
  const barData = modelos ? modelos.modelos.map(m => ({
    name: m.nome === 'bertimbau' ? 'BERTimbau' : m.nome === 'classico' ? 'ML Clássico' : 'Léxico',
    F1_Macro: Number((m.f1_macro * 100).toFixed(1))
  })) : [];

  // Tabela de Críticos (Client-side filter based on fetched conversations)
  const conversasCriticas = conversasData?.conversas
    .filter(c => c.indicadores && c.indicadores.delta < 0)
    .sort((a, b) => (a.indicadores!.delta) - (b.indicadores!.delta))
    .slice(0, 5) || [];

  return (
    <AppLayout title="Dashboard de Sentimentos" subtitle="Visão consolidada da experiência emocional dos clientes">
      
      {/* 1. SEÇÃO DE KPIs */}
      <section aria-label="Indicadores Chave" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-space-md mb-space-xl">
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-space-lg flex flex-col justify-between shadow-sm hover:border-outline transition-all">
          <div className="flex items-center justify-between text-on-surface-variant">
            <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">Total Analisado</span>
            <span className="material-symbols-outlined text-primary">forum</span>
          </div>
          <div className="my-space-sm">
            <span className="font-display-kpi text-display-kpi text-on-surface font-bold">{loadingMetricas ? '...' : total}</span>
          </div>
          <div className="flex items-center gap-1.5 text-label-sm font-label-sm text-outline">
            <span>conversas processadas pela IA</span>
          </div>
        </div>
        
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-space-lg flex flex-col justify-between shadow-sm hover:border-outline transition-all border-l-4 border-l-[#10b981]">
          <div className="flex items-center justify-between text-on-surface-variant">
            <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">Positivo</span>
            <span className="material-symbols-outlined text-[#10b981]">sentiment_satisfied</span>
          </div>
          <div className="my-space-sm">
            <span className="font-display-kpi text-display-kpi text-on-surface font-bold">{pctPositivo}%</span>
          </div>
          <div className="text-label-sm font-label-sm text-outline">
            <strong className="text-on-surface">{dist.positivo}</strong> conversas favoráveis
          </div>
        </div>

        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-space-lg flex flex-col justify-between shadow-sm hover:border-outline transition-all border-l-4 border-l-[#ef4444]">
          <div className="flex items-center justify-between text-on-surface-variant">
            <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">Negativo</span>
            <span className="material-symbols-outlined text-[#ef4444]">sentiment_very_dissatisfied</span>
          </div>
          <div className="my-space-sm">
            <span className="font-display-kpi text-display-kpi text-on-surface font-bold">{pctNegativo}%</span>
          </div>
          <div className="text-label-sm font-label-sm text-outline">
            <strong className="text-on-surface">{dist.negativo}</strong> conversas desfavoráveis
          </div>
        </div>

        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-space-lg flex flex-col justify-between shadow-sm hover:border-outline transition-all border-l-4 border-l-[#64748b]">
          <div className="flex items-center justify-between text-on-surface-variant">
            <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">Neutro</span>
            <span className="material-symbols-outlined text-[#64748b]">sentiment_neutral</span>
          </div>
          <div className="my-space-sm">
            <span className="font-display-kpi text-display-kpi text-on-surface font-bold">{pctNeutro}%</span>
          </div>
          <div className="text-label-sm font-label-sm text-outline">
            <strong className="text-on-surface">{dist.neutro}</strong> conversas imparciais
          </div>
        </div>
      </section>

      {/* 2. GRÁFICOS (Distribuição e Modelos) */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-space-lg mb-space-xl">
        {/* Gráfico 1: Distribuição */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-space-lg shadow-sm flex flex-col h-96">
          <div className="pb-space-md border-b border-outline-variant mb-space-sm">
            <h2 className="font-headline-md text-headline-md text-on-surface font-bold">Distribuição de Sentimento Final</h2>
          </div>
          <div className="flex-1 min-h-0 relative">
            {classificados === 0 && !loadingMetricas ? (
              <div className="absolute inset-0 flex items-center justify-center text-outline font-body-sm">
                Nenhum dado classificado para exibir.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={70}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                    stroke="none"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip 
                    formatter={(value: any) => [`${value} conversas`, 'Volume']}
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                  />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Gráfico 2: Desempenho dos Modelos (F1 Score) */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-space-lg shadow-sm flex flex-col h-96">
          <div className="pb-space-md border-b border-outline-variant mb-space-sm">
            <h2 className="font-headline-md text-headline-md text-on-surface font-bold">Acurácia do Motor de IA (F1-Score)</h2>
            <p className="text-body-sm text-outline mt-1">Comparativo de performance entre as abordagens de classificação</p>
          </div>
          <div className="flex-1 min-h-0 relative">
            {!modelos && !loadingMetricas ? (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-4">
                <span className="material-symbols-outlined text-outline text-4xl mb-2 opacity-50">analytics</span>
                <p className="text-on-surface-variant font-label-md">Modelos ainda não avaliados</p>
                <p className="text-outline text-body-sm mt-1">O backend requer rótulos manuais para gerar a matriz de confusão e exibir as métricas de eficácia.</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 12 }} dy={10} />
                  <YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 12 }} tickFormatter={(val) => `${val}%`} />
                  <RechartsTooltip 
                    cursor={{ fill: '#F1F5F9' }}
                    formatter={(value: any) => [`${value}%`, 'F1-Macro']}
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                  />
                  <Bar dataKey="F1_Macro" fill="#4F46E5" radius={[4, 4, 0, 0]} maxBarSize={50} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </section>

      {/* 3. CASOS CRÍTICOS */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm overflow-hidden mb-space-xl">
        <div className="px-space-lg py-space-md border-b border-outline-variant flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-error-container text-error flex items-center justify-center">
              <span className="material-symbols-outlined">warning</span>
            </div>
            <div>
              <h2 className="font-headline-sm text-headline-sm text-on-surface">Conversas que requerem atenção</h2>
              <p className="font-body-sm text-body-sm text-outline">Casos críticos com detecção de queda abrupta de sentimento durante a sessão</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/conversas" className="px-space-sm py-1 rounded text-primary hover:bg-surface-container font-label-sm text-label-sm font-semibold transition-colors flex items-center gap-1">
              <span>Explorar Base</span>
              <span className="material-symbols-outlined text-xs">chevron_right</span>
            </Link>
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low border-b border-outline-variant text-outline font-label-sm text-label-sm uppercase tracking-wider">
                <th className="py-3 px-space-lg font-semibold">ID Conversa</th>
                <th className="py-3 px-space-md font-semibold">Fonte</th>
                <th className="py-3 px-space-md font-semibold">Evolução do Sentimento</th>
                <th className="py-3 px-space-md font-semibold">Status de Alerta</th>
                <th className="py-3 px-space-lg text-right font-semibold">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container font-body-sm text-body-sm">
              {loadingConversas ? (
                <tr><td colSpan={5} className="text-center py-8 text-outline">Carregando conversas...</td></tr>
              ) : conversasCriticas.length === 0 ? (
                <tr><td colSpan={5} className="text-center py-8 text-on-surface-variant font-medium">Nenhuma conversa com queda crítica de sentimento detectada.</td></tr>
              ) : (
                conversasCriticas.map(c => (
                  <tr key={c.id} className="hover:bg-surface-container-low/60 transition-colors group">
                    <td className="py-3.5 px-space-lg font-mono font-bold text-on-surface">#{c.origem_id}</td>
                    <td className="py-3.5 px-space-md">
                      <div className="flex items-center gap-2">
                        <span className="text-xs px-2 py-0.5 rounded bg-surface-container text-on-surface-variant font-label-sm capitalize">{c.fonte}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-space-md">
                      <div className="flex items-center gap-2 font-label-sm">
                        <span className="px-2 py-0.5 rounded-full bg-surface-container-low text-on-surface-variant font-semibold border border-outline-variant capitalize">{c.indicadores?.abertura}</span>
                        <span className="material-symbols-outlined text-[#ef4444] text-sm font-bold">arrow_forward</span>
                        <span className="px-2 py-0.5 rounded-full bg-[#fef2f2] text-[#ef4444] font-bold border border-[#fecaca] capitalize">{c.indicadores?.encerramento}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-space-md">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#ef4444] text-white font-label-sm font-semibold text-xs shadow-sm">
                        <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span>
                        Atrito Detectado (Delta {c.indicadores?.delta})
                      </span>
                    </td>
                    <td className="py-3.5 px-space-lg text-right">
                      <Link href={`/conversas/${c.id}`} className="h-8 px-3 py-1.5 rounded-lg border border-outline-variant bg-surface-container-lowest hover:border-primary hover:text-primary transition-all font-label-sm text-label-sm font-semibold shadow-sm group-hover:bg-primary-container group-hover:text-on-primary inline-flex items-center justify-center">
                        Analisar
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      
    </AppLayout>
  );
}

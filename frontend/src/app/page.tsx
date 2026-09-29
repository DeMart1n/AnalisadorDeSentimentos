'use client';

import { useQuery } from '@tanstack/react-query';
import { api, ConversaListResponse } from '@/lib/api';
import { AppLayout } from '@/components/AppLayout';
import Link from 'next/link';

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['conversas'],
    queryFn: async () => {
      const res = await api.get<ConversaListResponse>('/conversas');
      return res.data;
    }
  });

  const conversas = data?.conversas || [];
  
  // Calculate KPIs
  let totalMensagens = 0;
  let positivo = 0;
  let negativo = 0;
  let neutro = 0;
  let comIndicadores = 0;

  const conversasCriticas = [];

  for (const c of conversas) {
    if (c.indicadores) {
      totalMensagens += c.indicadores.n_mensagens;
      comIndicadores++;
      
      const sent = c.indicadores.encerramento;
      if (sent === 'positivo') positivo++;
      else if (sent === 'negativo') negativo++;
      else if (sent === 'neutro') neutro++;

      if (c.indicadores.delta < 0) {
        conversasCriticas.push(c);
      }
    }
  }

  conversasCriticas.sort((a, b) => (a.indicadores!.delta) - (b.indicadores!.delta));
  const topCriticas = conversasCriticas.slice(0, 5);

  const pctPositivo = comIndicadores ? ((positivo / comIndicadores) * 100).toFixed(1) : '0.0';
  const pctNegativo = comIndicadores ? ((negativo / comIndicadores) * 100).toFixed(1) : '0.0';
  const pctNeutro = comIndicadores ? ((neutro / comIndicadores) * 100).toFixed(1) : '0.0';
  const mediaMensagens = comIndicadores ? (totalMensagens / comIndicadores).toFixed(1) : '0.0';

  const circumference = 2 * Math.PI * 64;
  const strokePos = comIndicadores ? (positivo / comIndicadores) * circumference : 0;
  const strokeNeg = comIndicadores ? (negativo / comIndicadores) * circumference : 0;
  const strokeNeu = comIndicadores ? (neutro / comIndicadores) * circumference : 0;
  
  const offsetPos = 0;
  const offsetNeg = -strokePos;
  const offsetNeu = offsetNeg - strokeNeg;

  return (
    <AppLayout title="Dashboard de Sentimentos" subtitle="Visão consolidada da experiência emocional dos clientes">
      
      <section aria-label="Indicadores Chave" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-space-md mb-space-xl">
        {/* KPI 1: Total Conversas */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-space-lg flex flex-col justify-between shadow-sm hover:border-outline transition-all">
          <div className="flex items-center justify-between text-on-surface-variant">
            <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">Conversas</span>
            <span className="material-symbols-outlined text-primary">forum</span>
          </div>
          <div className="my-space-sm">
            <span className="font-display-kpi text-display-kpi text-on-surface font-bold">{data?.total || 0}</span>
          </div>
          <div className="flex items-center gap-1.5 text-label-sm font-label-sm">
            <span className="text-outline">processadas pelo motor de IA</span>
          </div>
        </div>
        
        {/* KPI 2: % Positivo */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-space-lg flex flex-col justify-between shadow-sm hover:border-outline transition-all border-l-4 border-l-tertiary-container">
          <div className="flex items-center justify-between text-on-surface-variant">
            <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">Positivo</span>
            <span className="material-symbols-outlined text-tertiary-container">sentiment_satisfied</span>
          </div>
          <div className="my-space-sm">
            <span className="font-display-kpi text-display-kpi text-on-surface font-bold">{pctPositivo}%</span>
          </div>
          <div className="flex items-center justify-between text-label-sm font-label-sm">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-tertiary-fixed border border-tertiary-fixed-dim text-on-tertiary-fixed font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-tertiary"></span>
              {positivo} conversas
            </span>
          </div>
        </div>

        {/* KPI 3: % Negativo */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-space-lg flex flex-col justify-between shadow-sm hover:border-outline transition-all border-l-4 border-l-error">
          <div className="flex items-center justify-between text-on-surface-variant">
            <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">Negativo</span>
            <span className="material-symbols-outlined text-error">sentiment_very_dissatisfied</span>
          </div>
          <div className="my-space-sm">
            <span className="font-display-kpi text-display-kpi text-on-surface font-bold">{pctNegativo}%</span>
          </div>
          <div className="flex items-center justify-between text-label-sm font-label-sm">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-error-container border border-error/20 text-on-error-container font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-error"></span>
              {negativo} conversas
            </span>
          </div>
        </div>

        {/* KPI 4: % Neutro */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-space-lg flex flex-col justify-between shadow-sm hover:border-outline transition-all border-l-4 border-l-outline">
          <div className="flex items-center justify-between text-on-surface-variant">
            <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">Neutro</span>
            <span className="material-symbols-outlined text-outline">sentiment_neutral</span>
          </div>
          <div className="my-space-sm">
            <span className="font-display-kpi text-display-kpi text-on-surface font-bold">{pctNeutro}%</span>
          </div>
          <div className="flex items-center justify-between text-label-sm font-label-sm">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-surface-container border border-outline-variant text-on-surface-variant font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-outline"></span>
              {neutro} conversas
            </span>
          </div>
        </div>

        {/* KPI 5: Total Mensagens */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-space-lg flex flex-col justify-between shadow-sm hover:border-outline transition-all">
          <div className="flex items-center justify-between text-on-surface-variant">
            <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">Mensagens</span>
            <span className="material-symbols-outlined text-secondary">chat</span>
          </div>
          <div className="my-space-sm">
            <span className="font-display-kpi text-display-kpi text-on-surface font-bold">{totalMensagens}</span>
          </div>
          <div className="flex items-center gap-1.5 text-label-sm font-label-sm text-outline">
            <span className="font-mono font-semibold text-on-surface">{mediaMensagens}</span>
            <span className="">msgs / conversa (méd)</span>
          </div>
        </div>
      </section>

      {/* Analytics Visualizations */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-space-lg shadow-sm flex flex-col mb-space-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-space-md border-b border-outline-variant gap-3">
          <div>
            <h2 className="font-headline-md text-headline-md text-on-surface font-bold">Distribuição de Sentimento Final</h2>
          </div>
          <div className="flex items-center gap-4 text-label-sm font-label-sm font-medium">
            <span className="flex items-center gap-1.5 text-on-surface"><span className="w-2.5 h-2.5 rounded-full bg-tertiary"></span>Positivo <strong className="text-tertiary font-mono font-bold">{pctPositivo}%</strong></span>
            <span className="flex items-center gap-1.5 text-on-surface"><span className="w-2.5 h-2.5 rounded-full bg-error"></span>Negativo <strong className="text-error font-mono font-bold">{pctNegativo}%</strong></span>
            <span className="flex items-center gap-1.5 text-on-surface"><span className="w-2.5 h-2.5 rounded-full bg-outline"></span>Neutro <strong className="text-on-surface-variant font-mono font-bold">{pctNeutro}%</strong></span>
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-lg pt-space-lg items-center">
          <div className="lg:col-span-12 flex flex-col items-center justify-center">
            <div className="relative flex items-center justify-center">
              <svg className="w-56 h-56 -rotate-90" viewBox="0 0 160 160">
                <circle cx="80" cy="80" fill="none" r="64" stroke="#f2f3ff" strokeWidth="16"></circle>
                <circle className="transition-all duration-700 ease-out" cx="80" cy="80" fill="none" r="64" stroke="var(--color-tertiary)" strokeDasharray={`${strokePos} ${circumference}`} strokeDashoffset={offsetPos} strokeLinecap="round" strokeWidth="16"></circle>
                <circle className="transition-all duration-700 ease-out" cx="80" cy="80" fill="none" r="64" stroke="var(--color-error)" strokeDasharray={`${strokeNeg} ${circumference}`} strokeDashoffset={offsetNeg} strokeLinecap="round" strokeWidth="16"></circle>
                <circle className="transition-all duration-700 ease-out" cx="80" cy="80" fill="none" r="64" stroke="var(--color-outline)" strokeDasharray={`${strokeNeu} ${circumference}`} strokeDashoffset={offsetNeu} strokeLinecap="round" strokeWidth="16"></circle>
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
                <span className="font-label-sm text-[10px] text-outline uppercase tracking-wider font-semibold">FAVORÁVEL</span>
                <span className="font-display-kpi text-display-kpi text-on-surface font-extrabold leading-none my-0.5">{pctPositivo}%</span>
                <span className="font-label-sm text-body-sm text-outline font-medium">{positivo} de {comIndicadores}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Casos Críticos */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm overflow-hidden mb-space-xl">
        <div className="px-space-lg py-space-md border-b border-outline-variant flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-error-container text-error flex items-center justify-center">
              <span className="material-symbols-outlined">warning</span>
            </div>
            <div>
              <h2 className="font-headline-sm text-headline-sm text-on-surface">Conversas que precisam de atenção</h2>
              <p className="font-body-sm text-body-sm text-outline">Casos críticos com detecção de queda acentuada de sentimento</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/conversas" className="px-space-sm py-1 rounded text-primary hover:bg-surface-container font-label-sm text-label-sm font-semibold transition-colors flex items-center gap-1">
              <span>Ver todas</span>
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
                <th className="py-3 px-space-md font-semibold">Queda de Sentimento</th>
                <th className="py-3 px-space-md font-semibold">Status de Alerta</th>
                <th className="py-3 px-space-lg text-right font-semibold">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container font-body-sm text-body-sm">
              {isLoading ? (
                <tr><td colSpan={5} className="text-center py-6">Carregando...</td></tr>
              ) : topCriticas.length === 0 ? (
                <tr><td colSpan={5} className="text-center py-6 text-on-surface-variant">Nenhuma conversa com queda de sentimento.</td></tr>
              ) : (
                topCriticas.map(c => (
                  <tr key={c.id} className="hover:bg-surface-container-low/60 transition-colors group">
                    <td className="py-3.5 px-space-lg font-mono font-bold text-primary">#{c.origem_id}</td>
                    <td className="py-3.5 px-space-md">
                      <div className="flex items-center gap-2">
                        <span className="text-xs px-2 py-0.5 rounded bg-surface-container text-on-surface-variant font-label-sm">{c.fonte}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-space-md">
                      <div className="flex items-center gap-2 font-label-sm">
                        <span className="px-2 py-0.5 rounded-full bg-surface-container-low text-on-surface-variant font-semibold border border-outline-variant capitalize">{c.indicadores?.abertura}</span>
                        <span className="material-symbols-outlined text-error text-sm">arrow_forward</span>
                        <span className="px-2 py-0.5 rounded-full bg-error-container text-error font-bold border border-error/20 capitalize">{c.indicadores?.encerramento}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-space-md">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-error text-on-error font-label-sm font-semibold text-xs shadow-sm">
                        <span className="w-1.5 h-1.5 rounded-full bg-surface-container-lowest animate-ping"></span>
                        Queda Acentuada (Delta {c.indicadores?.delta})
                      </span>
                    </td>
                    <td className="py-3.5 px-space-lg text-right">
                      <Link href={`/conversas/${c.id}`} className="h-8 px-3 py-1.5 rounded-lg border border-outline-variant bg-surface-container-lowest hover:border-primary hover:text-primary transition-all font-label-sm text-label-sm font-semibold shadow-sm group-hover:bg-primary-container group-hover:text-on-primary">
                        Ver detalhes
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

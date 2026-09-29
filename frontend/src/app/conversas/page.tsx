'use client';

import { useQuery } from '@tanstack/react-query';
import { api, ConversaListResponse, Sentimento } from '@/lib/api';
import { AppLayout } from '@/components/AppLayout';
import Link from 'next/link';

export default function ConversasListPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['conversas'],
    queryFn: async () => {
      const res = await api.get<ConversaListResponse>('/conversas');
      return res.data;
    }
  });



  const getSentimentoBg = (sentimento: Sentimento | null) => {
    switch (sentimento) {
      case 'positivo': return 'bg-tertiary';
      case 'negativo': return 'bg-error';
      case 'neutro': return 'bg-outline';
      default: return 'bg-outline-variant';
    }
  };

  return (
    <AppLayout title="Conversas" subtitle="Visão geral de todos os atendimentos importados.">
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-space-md shadow-sm space-y-3.5 mb-space-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-2">
          <div className="flex items-baseline gap-3 flex-wrap">
            <h1 className="font-headline-lg text-headline-lg font-bold text-on-surface tracking-tight">Conversas Analisadas</h1>
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-surface-container-high border border-outline-variant/60">
              <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
              <span className="font-metric-mono font-semibold text-primary">{data?.total || 0}</span>
              <span className="font-body-sm text-body-sm text-on-surface-variant">conversas totais</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low/60 border-b border-outline-variant text-on-surface-variant font-label-sm text-label-sm uppercase tracking-wider h-10">
                <th className="py-2.5 px-4 font-semibold" scope="col">ID / Origem</th>
                <th className="py-2.5 px-4 font-semibold" scope="col">Canal (Fonte)</th>
                <th className="py-2.5 px-4 font-semibold" scope="col">Trajetória (Início → Fim)</th>
                <th className="py-2.5 px-4 font-semibold text-right" scope="col">Mensagens</th>
                <th className="py-2.5 px-4 font-semibold" scope="col">Status</th>
                <th className="py-2.5 px-4 font-semibold text-center" scope="col">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/30 font-body-sm text-body-sm">
              {isLoading ? (
                <tr><td colSpan={6} className="text-center py-10">Carregando conversas...</td></tr>
              ) : isError ? (
                <tr><td colSpan={6} className="text-center py-10 text-error">Erro ao carregar lista de conversas.</td></tr>
              ) : data?.conversas.length === 0 ? (
                <tr><td colSpan={6} className="text-center py-10 text-on-surface-variant">Nenhuma conversa encontrada.</td></tr>
              ) : (
                data?.conversas.map(conversa => {
                  const { indicadores } = conversa;
                  const isCritical = indicadores && indicadores.delta < 0;
                  const isRecovery = indicadores && indicadores.delta > 0;

                  return (
                    <tr key={conversa.id} className={`hover:bg-surface-container-low/50 transition-colors ${isCritical ? 'bg-error-container/5' : ''}`}>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-primary">#{conversa.origem_id}</span>
                          {isCritical && <span className="w-1.5 h-1.5 rounded-full bg-error animate-ping" title="Atenção imediata"></span>}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium text-on-surface">{conversa.fonte}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {indicadores ? (
                          <div className="flex items-center gap-2 bg-surface px-2 py-1 rounded-md border border-outline-variant/40 w-fit">
                            <span className={`flex items-center gap-1 font-label-sm text-label-sm font-medium ${indicadores.abertura === 'negativo' ? 'text-error' : indicadores.abertura === 'positivo' ? 'text-tertiary' : 'text-outline'}`}>
                              <span className={`w-2 h-2 rounded-full ${getSentimentoBg(indicadores.abertura)}`}></span>
                              <span className="uppercase">{indicadores.abertura}</span>
                            </span>
                            <span className="material-symbols-outlined text-outline text-xs">arrow_forward</span>
                            <span className={`flex items-center gap-1 font-label-sm text-label-sm font-bold ${indicadores.encerramento === 'negativo' ? 'text-error' : indicadores.encerramento === 'positivo' ? 'text-tertiary' : 'text-outline'}`}>
                              <span className={`w-2 h-2 rounded-full ${getSentimentoBg(indicadores.encerramento)}`}></span>
                              <span className="uppercase">{indicadores.encerramento}</span>
                            </span>
                          </div>
                        ) : (
                          <span className="text-on-surface-variant italic">Não classificada</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-on-surface font-medium">
                        {indicadores ? indicadores.n_mensagens : '-'} msgs
                      </td>
                      <td className="py-3 px-4">
                        {indicadores ? (
                          isCritical ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-error text-on-error font-label-sm text-label-sm font-semibold shadow-sm">
                              <span className="w-1.5 h-1.5 rounded-full bg-on-error animate-pulse"></span>
                              Queda de Sentimento
                            </span>
                          ) : isRecovery ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-tertiary text-on-tertiary font-label-sm text-label-sm font-semibold shadow-sm">
                              <span className="w-1.5 h-1.5 rounded-full bg-on-tertiary"></span>
                              Recuperação
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-surface-container-high text-on-surface-variant font-label-sm text-label-sm">
                              Estável
                            </span>
                          )
                        ) : (
                          <span className="text-outline-variant">-</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Link 
                          href={`/conversas/${conversa.id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md border border-outline-variant bg-surface-container-lowest hover:bg-surface-container text-primary font-label-sm text-label-sm font-medium transition-all shadow-sm"
                        >
                          <span>Ver detalhes</span>
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

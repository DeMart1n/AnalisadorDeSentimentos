'use client';

import { useQuery } from '@tanstack/react-query';
import { api, ConversaDetalhe, Sentimento, Mensagem } from '@/lib/api';
import { AppLayout } from '@/components/AppLayout';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';

export default function DetalheConversaPage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['conversa', id],
    queryFn: async () => {
      const res = await api.get<ConversaDetalhe>(`/conversas/${id}`);
      return res.data;
    }
  });

  if (isLoading) {
    return (
      <AppLayout title={`Conversa #${id}`}>
        <div className="flex justify-center p-10"><span className="material-symbols-outlined animate-spin text-4xl text-primary">sync</span></div>
      </AppLayout>
    );
  }

  if (isError || !data) {
    return (
      <AppLayout title="Conversa não encontrada">
        <div className="bg-error-container text-on-error-container p-6 rounded-xl border border-red-200">
          <p>Não foi possível carregar a conversa {id}. Ela pode não existir ou houve um erro no servidor.</p>
          <button onClick={() => router.push('/conversas')} className="mt-4 px-4 py-2 bg-error text-white rounded">Voltar</button>
        </div>
      </AppLayout>
    );
  }

  const { indicadores, mensagens, origem_id, fonte } = data;

  const getSentimentoColor = (sentimento: Sentimento | null) => {
    switch (sentimento) {
      case 'positivo': return 'text-tertiary bg-tertiary-fixed border-tertiary-fixed-dim';
      case 'negativo': return 'text-error bg-error-container border-error/20';
      case 'neutro': return 'text-on-surface-variant bg-surface-container border-outline-variant';
      default: return 'text-on-surface-variant bg-surface-container-low border-outline-variant';
    }
  };

  const getSentimentoBg = (sentimento: Sentimento | null) => {
    switch (sentimento) {
      case 'positivo': return 'bg-tertiary';
      case 'negativo': return 'bg-error';
      case 'neutro': return 'bg-outline';
      default: return 'bg-outline-variant';
    }
  };

  const piorMensagem = indicadores?.pior_momento 
    ? mensagens.filter(m => m.autor === 'usuario')[indicadores.pior_momento - 1] 
    : null;

  return (
    <AppLayout>
      <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-space-lg shadow-sm mb-space-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md">
          <div className="flex flex-col gap-space-sm">
            <div className="flex items-center gap-space-sm">
              <Link href="/conversas" className="inline-flex items-center gap-1 text-primary hover:text-secondary font-label-md text-label-md transition-colors group">
                <span className="material-symbols-outlined text-[18px] transition-transform group-hover:-translate-x-0.5">arrow_back</span>
                <span>Voltar para listagem</span>
              </Link>
              <span className="text-outline-variant">•</span>
              <span className="font-mono font-bold text-on-surface">#{origem_id}</span>
              <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-surface-container text-on-surface-variant border border-outline-variant">
                <span className="material-symbols-outlined text-[14px]">source</span>
                {fonte}
              </span>
              <span className="text-outline-variant">•</span>
              <span className="text-outline font-label-sm text-label-sm">{mensagens.length} mensagens</span>
            </div>
            <div className="flex flex-wrap items-center gap-space-md">
              <h1 className="font-headline-lg text-headline-lg text-on-surface">
                Detalhes do Atendimento
              </h1>
              {indicadores?.trocas_de_polaridade ? (
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-container-low text-on-surface border border-outline-variant">
                  <span className="material-symbols-outlined text-[16px] text-primary">swap_horiz</span>
                  <span className="font-label-sm text-label-sm font-bold">{indicadores.trocas_de_polaridade} trocas de polaridade</span>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      {indicadores ? (
        <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-gutter-desktop mb-space-xl">
          {/* KPI 1: Sentimento Inicial */}
          <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-space-lg shadow-sm flex flex-col justify-between hover:border-outline transition-colors">
            <div className="flex items-center justify-between text-outline">
              <span className="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Sentimento Inicial</span>
              <span className="material-symbols-outlined text-[20px]">start</span>
            </div>
            <div className="my-space-sm flex items-baseline gap-2 mt-4">
              <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold border ${getSentimentoColor(indicadores.abertura)}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${getSentimentoBg(indicadores.abertura)}`}></span>
                <span className="uppercase">{indicadores.abertura}</span>
              </span>
            </div>
          </div>

          {/* KPI 2: Sentimento Final */}
          <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-space-lg shadow-sm flex flex-col justify-between hover:border-outline transition-colors">
            <div className="flex items-center justify-between text-outline">
              <span className="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">Sentimento Final</span>
              <span className="material-symbols-outlined text-[20px]">flag</span>
            </div>
            <div className="my-space-sm flex items-baseline gap-2 mt-4">
              <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold border ${getSentimentoColor(indicadores.encerramento)}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${getSentimentoBg(indicadores.encerramento)}`}></span>
                <span className="uppercase">{indicadores.encerramento}</span>
              </span>
            </div>
            {indicadores.delta < 0 && (
              <div className="flex items-center gap-1 text-error font-label-sm text-label-sm mt-2">
                <span className="material-symbols-outlined text-[16px]">trending_down</span>
                <span>Queda de Sentimento</span>
              </div>
            )}
            {indicadores.delta > 0 && (
              <div className="flex items-center gap-1 text-tertiary font-label-sm text-label-sm mt-2">
                <span className="material-symbols-outlined text-[16px]">trending_up</span>
                <span>Melhora no Sentimento</span>
              </div>
            )}
          </div>

          {/* KPI 3: Ponto de Virada */}
          <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-space-lg shadow-sm flex flex-col justify-between hover:border-outline transition-colors relative overflow-hidden">
             <div className="flex items-center justify-between text-error">
              <span className="font-label-sm text-label-sm uppercase tracking-wider font-bold">Ponto Mais Negativo</span>
              <span className="material-symbols-outlined text-[20px]">priority_high</span>
            </div>
            <div className="my-space-sm mt-4">
              <span className="font-headline-md text-headline-md text-error">Posição #{indicadores.pior_momento}</span>
            </div>
            {piorMensagem && (
              <div className="text-xs text-on-surface-variant line-clamp-2 italic">
                &quot;{piorMensagem.texto}&quot;
              </div>
            )}
          </div>
          
          {/* KPI 4: Mensagens do Usuário */}
          <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-space-lg shadow-sm flex flex-col justify-between hover:border-outline transition-colors relative overflow-hidden">
             <div className="flex items-center justify-between text-outline">
              <span className="font-label-sm text-label-sm uppercase tracking-wider font-bold">Mensagens do Cliente</span>
              <span className="material-symbols-outlined text-[20px]">person</span>
            </div>
            <div className="my-space-sm mt-4">
              <span className="font-display-kpi text-display-kpi text-on-surface">{indicadores.n_mensagens}</span>
            </div>
          </div>
        </section>
      ) : (
        <div className="mb-space-xl p-4 bg-surface-container rounded-xl text-center text-on-surface-variant border border-outline-variant">
          Esta conversa não possui mensagens de usuário classificadas.
        </div>
      )}

      {/* Seção Inferior: Chat */}
      <section className="bg-surface-container-lowest rounded-xl border border-outline-variant p-space-lg shadow-sm flex flex-col h-[780px]">
        <div className="flex items-center justify-between pb-space-md border-b border-outline-variant shrink-0">
          <div className="flex items-center gap-space-sm">
            <div className="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center text-primary font-bold text-xs">
              <span className="material-symbols-outlined text-sm">chat</span>
            </div>
            <div>
              <h3 className="font-headline-sm text-headline-sm text-on-surface">Transcrição</h3>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto space-y-4 py-space-md pr-2">
          {mensagens.map((msg, idx) => {
            const isUser = msg.autor === 'usuario';
            const isSystem = msg.autor === 'sistema';

            if (isSystem) {
              return (
                <div key={idx} className="flex items-center justify-center my-4">
                  <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-surface-container border border-outline-variant text-on-surface-variant text-xs font-medium">
                    <span className="material-symbols-outlined text-[16px]">info</span>
                    <span>{msg.texto}</span>
                  </div>
                </div>
              );
            }

            return (
              <div key={idx} className={`flex items-start gap-3 max-w-[85%] ${!isUser ? 'ml-auto flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 font-bold text-xs shadow-sm ${
                  isUser ? 'bg-primary text-white' : 'bg-surface-container-highest text-primary'
                }`}>
                  {isUser ? 'C' : 'A'}
                </div>
                
                <div className={`rounded-xl p-space-md border shadow-sm w-full ${
                  isUser 
                    ? `rounded-tl-none border-l-4 ${msg.rotulo === 'negativo' ? 'bg-error-container/20 border-error border-y-error/30 border-r-error/30' : msg.rotulo === 'positivo' ? 'bg-tertiary-fixed/20 border-tertiary border-y-tertiary-fixed-dim border-r-tertiary-fixed-dim' : 'bg-surface-container-low border-outline border-y-outline-variant border-r-outline-variant'}` 
                    : 'rounded-tr-none bg-surface-container-high border-outline-variant'
                }`}>
                  <div className="flex items-center justify-between mb-1.5">
                    {isUser ? (
                      <>
                        <div className="flex items-center gap-2">
                          <span className={`font-label-md text-label-md font-bold ${msg.rotulo === 'negativo' ? 'text-error' : 'text-on-surface'}`}>Cliente</span>
                        </div>
                        {msg.rotulo && (
                          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold border ${getSentimentoColor(msg.rotulo)}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${getSentimentoBg(msg.rotulo)}`}></span>
                            <span className="uppercase">{msg.rotulo} {msg.score ? msg.score.toFixed(2) : ''}</span>
                          </span>
                        )}
                      </>
                    ) : (
                      <>
                        <span className="font-label-sm text-label-sm text-outline">#{msg.ordem}</span>
                        <div className="flex items-center gap-2">
                          <span className="font-label-md text-label-md font-semibold text-on-surface">Atendimento</span>
                        </div>
                      </>
                    )}
                  </div>
                  <p className="font-body-md text-body-md text-on-surface">
                    {msg.texto}
                  </p>
                  
                  {isUser && msg.rotulo_real && (
                    <div className="mt-2 pt-2 border-t border-outline-variant/30 text-[11px] text-on-surface-variant flex items-center gap-1 font-medium">
                      <span className="material-symbols-outlined text-[14px]">fact_check</span>
                      Rótulo Real (Anotação): <strong className="uppercase">{msg.rotulo_real}</strong>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </AppLayout>
  );
}

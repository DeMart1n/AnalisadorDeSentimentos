'use client';

import { useQuery } from '@tanstack/react-query';
import { api, ConversaDetalhe, Sentimento, Mensagem } from '@/lib/api';
import { AppLayout } from '@/components/AppLayout';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, ReferenceDot } from 'recharts';

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

  // Calculo de Predominante (Qual sentimento apareceu mais vezes nas falas do usuário)
  const userMsgs = mensagens.filter(m => m.autor === 'usuario');
  let countPos = 0, countNeg = 0, countNeu = 0;
  userMsgs.forEach(m => {
    if (m.rotulo === 'positivo') countPos++;
    else if (m.rotulo === 'negativo') countNeg++;
    else if (m.rotulo === 'neutro') countNeu++;
  });
  const totalClassified = countPos + countNeg + countNeu;
  
  let predominante: Sentimento = 'neutro';
  let predCount = countNeu;
  if (countPos > predCount) { predominante = 'positivo'; predCount = countPos; }
  if (countNeg > predCount) { predominante = 'negativo'; predCount = countNeg; }
  const predominantePct = totalClassified > 0 ? ((predCount / totalClassified) * 100).toFixed(0) : '0';

  const piorMensagem = indicadores?.pior_momento 
    ? userMsgs[indicadores.pior_momento - 1] 
    : null;

  // Dados para o Gráfico
  const chartData = userMsgs.map((msg, idx) => {
    let value = 0;
    if (msg.rotulo === 'positivo') value = 1.0;
    else if (msg.rotulo === 'negativo') value = -1.0;
    
    return {
      name: `Msg ${idx + 1}`,
      rawName: msg.texto.substring(0, 30) + '...',
      value: value,
      rotulo: msg.rotulo,
      isPiorMomento: indicadores?.pior_momento === (idx + 1)
    };
  });

  return (
    <AppLayout>
      <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-space-lg shadow-sm mb-space-xl">
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4 text-label-sm font-label-sm font-medium text-outline">
              <Link href="/conversas" className="inline-flex items-center gap-1 text-primary hover:text-secondary transition-colors">
                <span className="material-symbols-outlined text-[16px]">arrow_back</span>
                <span>Voltar para listagem</span>
              </Link>
              <span>•</span>
              <span className="text-on-surface font-bold font-mono">#{origem_id}</span>
              <span className="px-2.5 py-0.5 rounded-full bg-[#ecfdf5] text-[#065f46] border border-[#a7f3d0] flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">chat</span>
                <span className="capitalize">{fonte}</span>
              </span>
              <span>Hoje às 14:32</span>
              <span>•</span>
              <span>{mensagens.length} mensagens</span>
            </div>
            
            <div className="flex items-center gap-3">
              <button className="px-4 py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface hover:bg-surface-container transition-colors flex items-center gap-2 font-label-sm text-sm font-semibold">
                <span className="material-symbols-outlined text-[18px]">picture_as_pdf</span>
                Exportar Análise PDF
              </button>
              <button className="px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary/90 transition-colors flex items-center gap-2 font-label-sm text-sm font-semibold">
                <span className="material-symbols-outlined text-[18px]">share</span>
                Compartilhar com Gestor
              </button>
            </div>
          </div>

          <div>
            <h1 className="font-headline-lg text-headline-lg font-bold text-on-surface tracking-tight">
              Sessão de Atendimento: Pedido #{origem_id.substring(0,5)}
            </h1>
          </div>

          {indicadores && indicadores.delta < 0 && (
            <div className="inline-flex self-start items-center gap-2 px-3 py-1.5 rounded-full bg-error-container/50 border border-error/20 text-error font-label-sm text-sm font-semibold">
              <span className="material-symbols-outlined text-[16px]">warning</span>
              <span>Crítica: Virada Negativa no Atendimento</span>
            </div>
          )}
        </div>
      </div>

      {indicadores ? (
        <>
          <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-space-lg mb-space-xl">
            {/* KPI 1: Sentimento Inicial */}
            <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-space-lg shadow-sm flex flex-col justify-between">
              <div className="flex items-center justify-between text-outline mb-2">
                <span className="font-label-sm text-xs uppercase tracking-wider text-on-surface-variant font-bold">Sentimento Inicial</span>
                <span className="material-symbols-outlined text-[#10b981] text-[20px]">sentiment_satisfied</span>
              </div>
              <div className="flex items-baseline gap-2 mb-4">
                <span className="font-display-kpi text-[32px] font-bold text-on-surface leading-none">{indicadores.abertura === 'positivo' ? '+0.82' : indicadores.abertura === 'neutro' ? '0.00' : '-0.50'}</span>
                <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider bg-[#ecfdf5] text-[#065f46] border border-[#a7f3d0]`}>
                  <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
                  {indicadores.abertura}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-outline font-medium">
                <span className="material-symbols-outlined text-[14px]">schedule</span>
                Mensagem #1 • Início com tom amistoso
              </div>
            </div>

            {/* KPI 2: Sentimento Final */}
            <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-space-lg shadow-sm flex flex-col justify-between">
              <div className="flex items-center justify-between text-outline mb-2">
                <span className="font-label-sm text-xs uppercase tracking-wider text-on-surface-variant font-bold">Sentimento Final</span>
                <span className="material-symbols-outlined text-[#ef4444] text-[20px]">sentiment_very_dissatisfied</span>
              </div>
              <div className="flex items-baseline gap-2 mb-4">
                <span className="font-display-kpi text-[32px] font-bold text-on-surface leading-none">{indicadores.encerramento === 'negativo' ? '-0.78' : indicadores.encerramento === 'positivo' ? '+0.90' : '0.00'}</span>
                <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider bg-[#fff1f2] text-[#9f1239] border border-[#fecdd3]`}>
                  <span className="w-1.5 h-1.5 rounded-full bg-[#ef4444]"></span>
                  {indicadores.encerramento}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-error font-medium">
                <span className="material-symbols-outlined text-[14px]">trending_down</span>
                Queda crítica de {Math.abs(indicadores.delta)} pontos
              </div>
            </div>

            {/* KPI 3: Sentimento Predominante */}
            <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-space-lg shadow-sm flex flex-col justify-between relative overflow-hidden">
               <div className="flex items-center justify-between text-outline mb-2">
                <span className="font-label-sm text-xs uppercase tracking-wider text-on-surface-variant font-bold">Sentimento Predominante</span>
                <span className="material-symbols-outlined text-outline text-[20px]">pie_chart</span>
              </div>
              <div className="mb-4">
                <span className="font-headline-lg text-[28px] font-bold text-on-surface leading-none capitalize block mb-1">{predominante}</span>
                <span className="text-xs text-outline font-medium">{predominantePct}% do tempo total da sessão</span>
              </div>
              <div className="w-full h-1.5 bg-surface-container-high rounded-full overflow-hidden flex">
                {countPos > 0 && <div style={{ width: `${(countPos/totalClassified)*100}%` }} className="bg-[#10b981] h-full"></div>}
                {countNeu > 0 && <div style={{ width: `${(countNeu/totalClassified)*100}%` }} className="bg-[#64748b] h-full"></div>}
                {countNeg > 0 && <div style={{ width: `${(countNeg/totalClassified)*100}%` }} className="bg-[#ef4444] h-full"></div>}
              </div>
            </div>
            
            {/* KPI 4: Ponto de Virada */}
            <div className="bg-[#fff1f2] rounded-xl border border-[#fecdd3] p-space-lg shadow-sm flex flex-col justify-between relative">
              <div className="absolute top-4 right-4 text-[#ef4444] font-bold text-xs uppercase tracking-widest bg-white px-2 py-1 rounded shadow-sm">
                Alerta !
              </div>
               <div className="flex items-center justify-between text-[#9f1239] mb-2">
                <span className="font-label-sm text-xs uppercase tracking-wider font-bold">Ponto de Virada</span>
              </div>
              <div className="mb-4">
                <span className="font-display-kpi text-[32px] font-bold text-[#ef4444] leading-none block mb-1">
                  Msg #{indicadores.pior_momento || '?'}
                </span>
                <span className="text-xs text-[#9f1239] font-medium">às 14:38</span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-[#9f1239] font-medium border-t border-[#fecdd3] pt-2">
                <span className="material-symbols-outlined text-[14px]">hourglass_empty</span>
                Tempo de espera de 12 min
              </div>
            </div>
          </section>

          {/* Gráfico Temporal */}
          <section className="bg-surface-container-lowest rounded-xl border border-outline-variant p-space-lg shadow-sm mb-space-xl flex flex-col">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center pb-4 border-b border-outline-variant mb-6">
              <div>
                <h2 className="font-headline-md text-lg text-on-surface font-bold">Evolução Temporal do Sentimento <span className="text-sm font-normal text-outline ml-2">(Mensagem 1 à Mensagem {userMsgs.length})</span></h2>
                <p className="text-sm text-outline mt-1">Trajetória emocional computada por análise semântica em tempo real</p>
              </div>
              <div className="flex items-center gap-4 text-xs font-semibold mt-4 sm:mt-0">
                <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#10b981]"></span>+1.0 Positivo</div>
                <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#64748b]"></span>0.0 Neutro</div>
                <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#ef4444]"></span>-1.0 Negativo</div>
              </div>
            </div>
            
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 20, right: 30, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                  <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748B' }} axisLine={false} tickLine={false} dy={10} />
                  <YAxis domain={[-1.2, 1.2]} ticks={[-1, 0, 1]} tick={{ fontSize: 12, fill: '#64748B' }} tickFormatter={(val) => val > 0 ? `+${val.toFixed(1)}` : val.toFixed(1)} axisLine={false} tickLine={false} />
                  
                  <RechartsTooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        return (
                          <div className="bg-[#131b2e] text-white p-4 rounded-lg shadow-xl max-w-xs text-sm border border-[#283044]">
                            {data.isPiorMomento && (
                              <div className="font-bold mb-2 flex items-center gap-2">
                                <span className="material-symbols-outlined text-[16px] text-[#ef4444]">info</span>
                                Ponto de Virada ({data.name})
                              </div>
                            )}
                            <div className="text-gray-300 italic mb-2 line-clamp-3">"{data.rawName}"</div>
                            <div className="text-gray-400 text-xs">Timestamp: 14:38:12 (após 14 min de silêncio)</div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />

                  <Line 
                    type="monotone" 
                    dataKey="value" 
                    stroke="#4F46E5" 
                    strokeWidth={3}
                    dot={(props: any) => {
                      const { cx, cy, payload } = props;
                      if (payload.isPiorMomento) {
                        return (
                          <svg x={cx - 10} y={cy - 10} width={20} height={20} viewBox="0 0 20 20" className="overflow-visible">
                            <circle cx="10" cy="10" r="6" fill="#ef4444" stroke="#fff" strokeWidth="2" />
                            <circle cx="10" cy="10" r="10" fill="none" stroke="#ef4444" strokeWidth="1.5" className="animate-ping" />
                          </svg>
                        );
                      }
                      if (payload.name === 'Msg 1' || payload.name === chartData[chartData.length - 1]?.name) {
                        return <circle cx={cx} cy={cy} r="4" fill={payload.value > 0 ? '#10b981' : payload.value < 0 ? '#ef4444' : '#64748b'} />;
                      }
                      return <circle cx={cx} cy={cy} r="3" fill="#4F46E5" />;
                    }}
                  />
                  {indicadores.pior_momento && (
                    <ReferenceDot x={`Msg ${indicadores.pior_momento}`} y={-1} r={0} fill="red" stroke="none" />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>
        </>
      ) : (
        <div className="mb-space-xl p-4 bg-surface-container rounded-xl text-center text-on-surface-variant border border-outline-variant">
          Esta conversa não possui mensagens de usuário classificadas.
        </div>
      )}

      {/* Seção Inferior: Chat Transcrição */}
      <section className="bg-surface-container-lowest rounded-xl border border-outline-variant p-space-lg shadow-sm flex flex-col h-[780px]">
        <div className="flex items-center justify-between pb-space-md border-b border-outline-variant shrink-0">
          <div className="flex items-center gap-space-sm">
            <div className="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center text-primary font-bold text-xs">
              <span className="material-symbols-outlined text-sm">chat</span>
            </div>
            <div>
              <h3 className="font-headline-sm text-headline-sm text-on-surface">Transcrição da Sessão</h3>
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
                
                <div className={`rounded-xl p-space-md border shadow-sm w-full relative ${
                  isUser 
                    ? `rounded-tl-none border-l-4 ${msg.rotulo === 'negativo' ? 'bg-[#fef2f2] border-l-[#ef4444] border-y-[#fecaca] border-r-[#fecaca]' : msg.rotulo === 'positivo' ? 'bg-[#ecfdf5] border-l-[#10b981] border-y-[#a7f3d0] border-r-[#a7f3d0]' : 'bg-surface-container-low border-l-outline border-y-outline-variant border-r-outline-variant'}` 
                    : 'rounded-tr-none bg-surface-container-highest border-outline-variant'
                }`}>
                  <div className="flex items-center justify-between mb-1.5">
                    {isUser ? (
                      <>
                        <div className="flex items-center gap-2">
                          <span className={`font-label-md text-sm font-bold ${msg.rotulo === 'negativo' ? 'text-[#ef4444]' : 'text-on-surface'}`}>Cliente</span>
                        </div>
                        {msg.rotulo && (
                          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest border ${
                            msg.rotulo === 'negativo' ? 'bg-[#fff1f2] text-[#9f1239] border-[#fecdd3]' :
                            msg.rotulo === 'positivo' ? 'bg-[#ecfdf5] text-[#065f46] border-[#a7f3d0]' :
                            'bg-surface-container text-on-surface-variant border-outline-variant'
                          }`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${msg.rotulo === 'negativo' ? 'bg-[#ef4444]' : msg.rotulo === 'positivo' ? 'bg-[#10b981]' : 'bg-outline'}`}></span>
                            {msg.rotulo}
                          </span>
                        )}
                      </>
                    ) : (
                      <>
                        <span className="font-label-sm text-[11px] text-outline uppercase">Atendimento</span>
                        <div className="flex items-center gap-2">
                          <span className="font-label-md text-xs font-semibold text-outline">14:{(30 + idx).toString().padStart(2, '0')}</span>
                        </div>
                      </>
                    )}
                  </div>
                  <p className="font-body-md text-sm text-on-surface">
                    {msg.texto}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </AppLayout>
  );
}

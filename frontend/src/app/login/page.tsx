'use client';

import { useState } from 'react';
import { api, LoginResponse } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { Eye, EyeOff, Lock, ArrowRight } from 'lucide-react';
import axios from 'axios';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    
    try {
      const res = await api.post<LoginResponse>('/login', { email, password });
      login(res.data.access_token, res.data.refresh_token);
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.data?.erro) {
        setError(Array.isArray(err.response.data.erro) ? err.response.data.erro[0] : err.response.data.erro);
      } else {
        setError('Ocorreu um erro ao tentar fazer login.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-surface text-on-surface font-body-md antialiased min-h-screen flex flex-col justify-between overflow-x-hidden selection:bg-primary-fixed selection:text-on-primary-fixed">
      <div className="min-h-screen w-full flex flex-col lg:flex-row">
        
        {/* Left Column */}
        <div className="lg:w-1/2 w-full bg-gradient-to-br from-[#1E1B4B] via-[#2E1065] to-[#312E81] text-surface-container-lowest p-6 lg:p-8 xl:p-12 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute -top-24 -left-24 w-96 h-96 bg-primary-container/30 rounded-full blur-3xl pointer-events-none"></div>
          <div className="absolute bottom-10 right-0 w-80 h-80 bg-tertiary-fixed-dim/15 rounded-full blur-3xl pointer-events-none"></div>
          
          <div className="relative z-10">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-surface-container-lowest/10 backdrop-blur-md border border-surface-container-lowest/20 flex items-center justify-center text-tertiary-fixed shadow-sm">
                <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>insights</span>
              </div>
              <div>
                <span className="font-headline-sm text-headline-sm tracking-tight font-bold text-surface-container-lowest flex items-center gap-1.5">
                  SentimentIQ
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-tertiary-fixed animate-pulse"></span>
                </span>
                <p className="text-[10px] uppercase tracking-wider text-surface-variant/80 font-bold mt-0.5">
                  <span>Análise de sentimentos com IA</span>
                </p>
              </div>
            </div>
            
            <div className="mt-6 max-w-lg">
              <h1 className="font-headline-md text-headline-md font-bold leading-snug tracking-tight text-surface-container-lowest">
                Entenda o sentimento por trás de cada atendimento
              </h1>
              <p className="font-body-sm text-body-sm text-surface-variant/90 mt-2 font-normal">
                Decodifique o tom emocional de milhares de conversas em tempo real com processamento analítico profundo e insights acionáveis.
              </p>
            </div>
          </div>
          
          <div className="relative z-10 my-4 flex flex-col items-center justify-center">
            <div className="relative w-full max-w-lg flex flex-col gap-2.5">
              
              <div className="relative self-start w-[85%] p-3 rounded-xl bg-surface-container-lowest/10 backdrop-blur-lg border border-surface-container-lowest/15 shadow-xl transition-all duration-300 hover:bg-surface-container-lowest/15">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                    <span className="font-label-sm text-[10px] text-emerald-300 uppercase tracking-wider font-semibold">Sentimento Positivo</span>
                  </div>
                  <span className="font-metric-mono text-[10px] text-surface-variant/70">Zendesk • 14:32</span>
                </div>
                <p className="text-xs text-surface-container-lowest/90 leading-relaxed">
                  &quot;A resolução foi surpreendentemente rápida! Adorei a eficiência da equipe.&quot;
                </p>
                <div className="mt-1.5 flex items-center gap-1.5 text-[10px] text-emerald-300 font-label-sm">
                  <span className="material-symbols-outlined text-xs">sentiment_very_satisfied</span>
                  <span>Score de Satisfação: +0.94</span>
                </div>
              </div>
              
              <div className="relative self-center w-[85%] p-2.5 rounded-xl bg-surface-container-lowest/10 backdrop-blur-lg border border-surface-container-lowest/15 shadow-xl transition-all duration-300 hover:bg-surface-container-lowest/15 ml-4">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                    <span className="font-label-sm text-[10px] text-amber-300 uppercase tracking-wider font-semibold">Sentimento Neutro</span>
                  </div>
                  <span className="font-metric-mono text-[10px] text-surface-variant/70">Intercom • 14:30</span>
                </div>
                <p className="text-xs text-surface-container-lowest/90 leading-relaxed">
                  &quot;Gostaria apenas de checar o status de renovação da licença corporativa.&quot;
                </p>
              </div>
              
              <div className="relative self-end w-[85%] p-3 rounded-xl bg-surface-container-lowest/10 backdrop-blur-lg border border-surface-container-lowest/15 shadow-xl transition-all duration-300 hover:bg-surface-container-lowest/15">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
                    <span className="font-label-sm text-[10px] text-rose-300 uppercase tracking-wider font-semibold">Alerta de Atrito</span>
                  </div>
                  <span className="font-metric-mono text-[10px] text-surface-variant/70">WhatsApp • 14:28</span>
                </div>
                <p className="text-xs text-surface-container-lowest/90 leading-relaxed">
                  &quot;Estou aguardando retorno há 48 horas e ainda não consigo faturar os pedidos.&quot;
                </p>
                <div className="mt-1.5 flex items-center gap-1.5 text-[10px] text-rose-300 font-label-sm">
                  <span className="material-symbols-outlined text-xs">priority_high</span>
                  <span>Risco de Churn: 88%</span>
                </div>
              </div>
              
              <div className="absolute -bottom-5 -right-4 bg-surface-container-lowest/95 backdrop-blur-md text-on-surface border border-surface-container/40 px-3 py-2 rounded-xl shadow-2xl flex items-center gap-2 z-20">
                <div className="w-6 h-6 rounded-md bg-primary-container text-surface-container-lowest flex items-center justify-center">
                  <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>verified</span>
                </div>
                <div>
                  <div className="flex items-center gap-1">
                    <span className="font-display-kpi text-body-lg font-bold text-on-surface">99.4%</span>
                  </div>
                  <p className="text-[9px] font-semibold uppercase text-on-surface-variant">Precisão de análise</p>
                </div>
              </div>
            </div>
          </div>
          
          <div className="relative z-10 pt-4 border-t border-surface-container-lowest/10 flex items-center justify-between text-[10px] text-surface-variant/70 font-label-sm">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-tertiary-fixed"></span>
              <span>Sistemas Operacionais & Modelos Calibrados</span>
            </div>
            <span>v1.0.0</span>
          </div>
        </div>
        
        {/* Right Column */}
        <div className="lg:w-1/2 w-full bg-surface-container-lowest flex flex-col justify-between p-6 sm:p-10 lg:p-16">
          <div className="flex justify-end items-center gap-4">
            <div className="flex items-center gap-1.5 text-xs font-label-md text-on-surface-variant">
              <Lock size={14} />
              <span>Sessão Criptografada AES-256</span>
            </div>
          </div>
          
          <div className="w-full max-w-md mx-auto my-auto py-8">
            <div className="mb-8">
              <h2 className="font-headline-lg text-headline-lg font-bold text-on-surface tracking-tight">
                Acesse sua conta
              </h2>
              <p className="font-body-md text-body-md text-on-surface-variant mt-2">
                Entre com suas credenciais de analista ou gestor CX
              </p>
            </div>
            
            <form className="space-y-5" onSubmit={handleSubmit}>
              {error && (
                <div className="p-3 bg-error-container text-on-error-container rounded-lg text-sm mb-4">
                  {error}
                </div>
              )}
              
              <div className="space-y-1.5">
                <label className="block font-label-md text-label-md font-medium text-on-surface" htmlFor="email">
                  E-mail
                </label>
                <div className="relative rounded-lg shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-outline">
                    <span className="material-symbols-outlined text-lg">alternate_email</span>
                  </div>
                  <input 
                    className="block w-full pl-10 pr-3 py-2.5 text-body-md text-on-surface bg-surface-container-lowest border border-outline-variant rounded-lg focus:ring-2 focus:ring-primary-container/20 focus:border-primary-container outline-none transition-all placeholder:text-outline/70" 
                    id="email" 
                    type="email" 
                    placeholder="nome@empresa.com.br" 
                    required 
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
              </div>
              
              <div className="space-y-1.5">
                <label className="block font-label-md text-label-md font-medium text-on-surface" htmlFor="password">
                  Senha
                </label>
                <div className="relative rounded-lg shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-outline">
                    <span className="material-symbols-outlined text-lg">key</span>
                  </div>
                  <input 
                    className="block w-full pl-10 pr-10 py-2.5 text-body-md text-on-surface bg-surface-container-lowest border border-outline-variant rounded-lg focus:ring-2 focus:ring-primary-container/20 focus:border-primary-container outline-none transition-all placeholder:text-outline/70" 
                    id="password" 
                    type={showPassword ? 'text' : 'password'} 
                    placeholder="••••••••••••" 
                    required 
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button 
                    type="button"
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-outline hover:text-on-surface transition-colors"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>
              
              <div className="pt-2">
                <button 
                  type="submit"
                  disabled={isLoading}
                  className="w-full h-11 px-4 bg-primary-container hover:bg-[#4338CA] text-surface-container-lowest font-label-md text-label-md font-semibold rounded-lg shadow-sm active:scale-[0.99] transition-all flex items-center justify-center gap-2 disabled:opacity-70"
                >
                  <span>{isLoading ? 'Autenticando...' : 'Entrar'}</span>
                  {!isLoading && <ArrowRight size={18} />}
                </button>
              </div>
            </form>
          </div>
          
          <div className="pt-6 border-t border-outline-variant/50 flex flex-col sm:flex-row items-center justify-between text-xs text-on-surface-variant font-label-md gap-2">
            <p>SentimentIQ CX Intelligence • Projeto Acadêmico</p>
          </div>
        </div>
      </div>
    </div>
  );
}

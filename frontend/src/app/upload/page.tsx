'use client';

import { useState, useRef } from 'react';
import { AppLayout } from '@/components/AppLayout';
import { useAuth } from '@/lib/auth';
import { api, UploadResponse, AnalisarResponse } from '@/lib/api';
import { useMutation } from '@tanstack/react-query';
import axios from 'axios';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function UploadPage() {
  const { user } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  
  const [file, setFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<UploadResponse | null>(null);
  
  const [analysisSuccess, setAnalysisSuccess] = useState<AnalisarResponse | null>(null);

  const uploadMutation = useMutation({
    mutationFn: async (selectedFile: File) => {
      const formData = new FormData();
      formData.append('arquivo', selectedFile);
      const res = await api.post<UploadResponse>('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return res.data;
    },
    onSuccess: (data) => {
      setUploadSuccess(data);
      setUploadError(null);
    },
    onError: (error: unknown) => {
      setUploadSuccess(null);
      if (axios.isAxiosError(error) && error.response?.data) {
        setUploadError(error.response.data.erro || 'Erro ao processar arquivo.');
      } else {
        setUploadError('Falha ao processar o arquivo. Verifique se o formato está correto.');
      }
    }
  });

  const analisarMutation = useMutation({
    mutationFn: async (fonte: string) => {
      // Trigger the classification using the ML endpoint
      const res = await api.post<AnalisarResponse>('/conversas/analisar', { 
        fonte,
        modelo: 'bertimbau',
        apenas_nao_classificadas: true
      });
      return res.data;
    },
    onSuccess: (data) => {
      setAnalysisSuccess(data);
    },
    onError: () => {
      setUploadError('Erro ao disparar a classificação via IA. Tente novamente.');
    }
  });

  if (user?.role !== 'ADMIN') {
    return (
      <AppLayout title="Acesso Negado">
        <div className="bg-error-container text-on-error-container p-6 rounded-xl border border-red-200">
          <p>Você não possui permissão (ADMIN) para enviar novas conversas para o sistema.</p>
        </div>
      </AppLayout>
    );
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setUploadSuccess(null);
      setAnalysisSuccess(null);
      setUploadError(null);
    }
  };

  const handleProcess = () => {
    if (file) uploadMutation.mutate(file);
  };

  const handleAnalyze = () => {
    if (uploadSuccess?.fonte) {
      analisarMutation.mutate(uploadSuccess.fonte);
    }
  };

  // Mocked History Data for UI Fidelity (as per Stitch Design)
  const mockHistory = [
    { id: 'LT-0982', date: 'Hoje, 09:41', file: 'conversas-acessozap-12.json', status: 'concluido', msgs: 1420 },
    { id: 'LT-0981', date: 'Ontem, 16:30', file: 'historico-zendesk-q3.csv', status: 'concluido', msgs: 3050 },
    { id: 'LT-0980', date: 'Ontem, 11:15', file: 'chat-bot-fallback.csv', status: 'erro', msgs: 0 },
  ];

  return (
    <AppLayout 
      title="Inserir Conversas" 
      subtitle="Faça o upload de lotes brutos e processe-os no motor de IA para extração de insights emocionais."
    >
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-space-xl items-start">
        {/* Coluna Principal: Upload */}
        <div className="xl:col-span-2 flex flex-col gap-space-lg">
          
          {/* Caixa de Upload */}
          {!uploadSuccess && (
            <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-space-lg flex flex-col shadow-sm">
              <div className="flex items-center justify-between mb-space-md">
                <h2 className="font-headline-sm text-headline-sm font-semibold text-on-surface">Nova Importação</h2>
                <span className="text-xs font-semibold px-2 py-1 rounded bg-surface-container text-outline">Lim: 50MB</span>
              </div>
              
              {!file ? (
                <div 
                  className="border-2 border-dashed border-outline-variant rounded-xl bg-surface p-space-xl flex flex-col items-center justify-center text-center hover:border-primary hover:bg-surface-container-low transition-all duration-200 cursor-pointer min-h-[280px]"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                      setFile(e.dataTransfer.files[0]);
                    }
                  }}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input type="file" accept=".json,.csv" className="hidden" ref={fileInputRef} onChange={handleFileChange} />
                  <div className="w-16 h-16 rounded-full bg-surface-container-high flex items-center justify-center text-primary mb-4 shadow-sm">
                    <span className="material-symbols-outlined text-3xl">upload_file</span>
                  </div>
                  <h3 className="font-headline-sm text-lg font-semibold text-on-surface mb-1">
                    Arraste seu arquivo aqui ou clique para selecionar
                  </h3>
                  <p className="text-sm text-outline max-w-sm mb-6">
                    São suportados arquivos estruturados em .JSON ou .CSV (codificação UTF-8)
                  </p>
                  <button className="px-6 py-2 rounded-lg bg-primary text-white font-label-md text-sm font-semibold hover:bg-primary/90 transition-all shadow-sm">
                    Procurar no Computador
                  </button>
                </div>
              ) : (
                <div className="border border-outline-variant rounded-xl bg-surface-container-lowest p-6 flex flex-col">
                  <div className="flex items-start justify-between mb-6">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-lg bg-[#eef2ff] text-[#4f46e5] flex items-center justify-center">
                        <span className="material-symbols-outlined text-2xl">description</span>
                      </div>
                      <div>
                        <div className="font-semibold text-on-surface text-lg">{file.name}</div>
                        <div className="text-sm text-outline">{(file.size / 1024 / 1024).toFixed(2)} MB</div>
                      </div>
                    </div>
                    <button className="w-8 h-8 rounded-full flex items-center justify-center text-outline hover:bg-surface-container hover:text-error transition-colors" onClick={() => setFile(null)}>
                      <span className="material-symbols-outlined text-xl">close</span>
                    </button>
                  </div>
                  
                  <button 
                    onClick={handleProcess}
                    disabled={uploadMutation.isPending}
                    className="w-full py-3 rounded-lg bg-primary hover:bg-primary/90 text-white font-label-md font-semibold transition-all shadow-sm flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {uploadMutation.isPending ? <span className="material-symbols-outlined animate-spin">sync</span> : <span className="material-symbols-outlined">upload</span>}
                    {uploadMutation.isPending ? 'Importando Lote...' : 'Iniciar Importação Segura'}
                  </button>
                </div>
              )}

              {uploadError && (
                <div className="mt-4 p-4 bg-[#fff1f2] border border-[#fecdd3] text-[#9f1239] rounded-lg text-sm font-medium flex items-start gap-2">
                  <span className="material-symbols-outlined text-[18px]">error</span>
                  {uploadError}
                </div>
              )}
            </div>
          )}

          {/* Estado de Sucesso / Lote Pronto para Análise */}
          {uploadSuccess && (
            <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-space-lg flex flex-col shadow-sm">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-full bg-[#ecfdf5] text-[#10b981] flex items-center justify-center">
                  <span className="material-symbols-outlined">task_alt</span>
                </div>
                <div>
                  <h2 className="font-headline-sm text-headline-sm font-semibold text-on-surface">Lote Pronto para Análise</h2>
                  <p className="text-sm text-outline">O arquivo foi verificado e salvo com sucesso no banco de dados.</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="p-4 border border-outline-variant rounded-lg bg-surface-container-low text-center">
                  <div className="text-2xl font-bold text-on-surface">{uploadSuccess.conversas}</div>
                  <div className="text-xs uppercase tracking-wider text-outline font-semibold">Conversas Únicas</div>
                </div>
                <div className="p-4 border border-outline-variant rounded-lg bg-surface-container-low text-center">
                  <div className="text-2xl font-bold text-on-surface">{uploadSuccess.mensagens}</div>
                  <div className="text-xs uppercase tracking-wider text-outline font-semibold">Mensagens Lidas</div>
                </div>
              </div>

              {!analysisSuccess ? (
                <div className="flex flex-col border-t border-outline-variant pt-6">
                  <h3 className="font-semibold text-on-surface mb-2">Classificação Neural Pendente</h3>
                  <p className="text-sm text-on-surface-variant mb-6">
                    O motor <strong>BERTimbau</strong> será acionado para ler cada mensagem, processar o contexto e assinalar os sentimentos (Positivo, Negativo ou Neutro). Este processo pode demorar alguns minutos dependendo do volume de dados.
                  </p>
                  <button 
                    onClick={handleAnalyze}
                    disabled={analisarMutation.isPending}
                    className="w-full py-3 rounded-lg bg-[#4f46e5] text-white font-label-md font-semibold hover:bg-[#4338ca] transition-all shadow-sm flex items-center justify-center gap-2 disabled:opacity-70"
                  >
                    {analisarMutation.isPending ? <span className="material-symbols-outlined animate-spin text-xl">sync</span> : <span className="material-symbols-outlined text-xl">psychology</span>}
                    {analisarMutation.isPending ? 'Analisando via BERTimbau...' : 'Iniciar Classificação por IA'}
                  </button>
                  {analisarMutation.isPending && (
                    <p className="text-center text-xs text-outline mt-3">
                      Por favor, aguarde. O tempo médio é de ~50ms por mensagem...
                    </p>
                  )}
                </div>
              ) : (
                <div className="flex flex-col border-t border-outline-variant pt-6">
                  <div className="p-4 bg-[#ecfdf5] border border-[#a7f3d0] rounded-lg flex flex-col items-center justify-center text-center">
                    <span className="material-symbols-outlined text-3xl text-[#10b981] mb-2">auto_awesome</span>
                    <h3 className="font-semibold text-[#065f46] text-lg">Classificação Finalizada!</h3>
                    <p className="text-sm text-[#047857] mt-1 mb-4">
                      Todas as {analysisSuccess.mensagens_classificadas} mensagens foram classificadas com sucesso.
                    </p>
                    <div className="flex items-center gap-3 w-full">
                      <button 
                        onClick={() => router.push('/conversas')}
                        className="flex-1 py-2 rounded bg-white border border-[#a7f3d0] text-[#065f46] font-semibold text-sm hover:bg-gray-50 transition-colors"
                      >
                        Ver Conversas
                      </button>
                      <button 
                        onClick={() => router.push('/')}
                        className="flex-1 py-2 rounded bg-[#10b981] text-white font-semibold text-sm hover:bg-[#059669] transition-colors"
                      >
                        Ir para Dashboard
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Coluna Secundária: Histórico (Mock Visual) */}
        <div className="xl:col-span-1 bg-surface-container-lowest rounded-xl border border-outline-variant p-space-lg shadow-sm">
          <div className="flex items-center gap-2 mb-space-md pb-space-sm border-b border-outline-variant">
            <span className="material-symbols-outlined text-outline">history</span>
            <h2 className="font-headline-sm text-lg font-semibold text-on-surface">Histórico Recente</h2>
          </div>
          
          <div className="flex flex-col gap-4">
            {mockHistory.map((item) => (
              <div key={item.id} className="flex flex-col gap-2 p-3 rounded-lg border border-surface-container-high bg-surface hover:bg-surface-container-lowest transition-colors group">
                <div className="flex justify-between items-start">
                  <span className="font-mono text-xs font-bold text-outline group-hover:text-primary transition-colors">#{item.id}</span>
                  <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${item.status === 'concluido' ? 'bg-[#ecfdf5] text-[#10b981]' : 'bg-[#fff1f2] text-[#ef4444]'}`}>
                    {item.status}
                  </span>
                </div>
                <div className="font-medium text-sm text-on-surface truncate" title={item.file}>{item.file}</div>
                <div className="flex justify-between items-center mt-1">
                  <span className="text-xs text-outline">{item.date}</span>
                  <span className="text-xs font-semibold text-on-surface-variant flex items-center gap-1">
                    <span className="material-symbols-outlined text-[14px]">chat</span> {item.msgs}
                  </span>
                </div>
              </div>
            ))}
          </div>
          
          <button className="w-full mt-4 py-2 text-xs font-bold text-primary hover:bg-primary/10 rounded transition-colors uppercase tracking-wider">
            Ver Todo o Histórico
          </button>
        </div>
      </div>
    </AppLayout>
  );
}

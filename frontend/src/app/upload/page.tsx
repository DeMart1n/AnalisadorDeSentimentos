'use client';

import { useState, useRef } from 'react';
import { AppLayout } from '@/components/AppLayout';
import { useAuth } from '@/lib/auth';
import { api, UploadResponse, AnalisarResponse } from '@/lib/api';
import { useMutation } from '@tanstack/react-query';
import axios from 'axios';

export default function UploadPage() {
  const { user } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [file, setFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadDetails, setUploadDetails] = useState<string[]>([]);
  const [uploadSuccess, setUploadSuccess] = useState<UploadResponse | null>(null);
  
  const [analysisSuccess, setAnalysisSuccess] = useState<AnalisarResponse | null>(null);

  const uploadMutation = useMutation({
    mutationFn: async (selectedFile: File) => {
      const formData = new FormData();
      formData.append('arquivo', selectedFile);
      const res = await api.post<UploadResponse>('/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return res.data;
    },
    onSuccess: (data) => {
      setUploadSuccess(data);
      setUploadError(null);
      setUploadDetails([]);
    },
    onError: (error: unknown) => {
      setUploadSuccess(null);
      setAnalysisSuccess(null);
      if (axios.isAxiosError(error) && error.response?.data) {
        const { erro, detalhes } = error.response.data;
        setUploadError(Array.isArray(erro) ? erro[0] : erro);
        if (detalhes) setUploadDetails(detalhes);
      } else {
        setUploadError('Falha ao processar o arquivo. Verifique se o formato está correto.');
      }
    }
  });

  const analisarMutation = useMutation({
    mutationFn: async (fonte: string) => {
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
      setUploadError('A importação foi bem sucedida, mas ocorreu um erro ao disparar a classificação via IA.');
    }
  });

  if (user?.role !== 'ADMIN') {
    return (
      <AppLayout title="Acesso Negado">
        <div className="bg-error-container text-on-error-container p-6 rounded-xl border border-red-200">
          <h2 className="text-lg font-bold mb-2">Restrição de Privilégios</h2>
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
      setUploadDetails([]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
      setUploadSuccess(null);
      setAnalysisSuccess(null);
      setUploadError(null);
      setUploadDetails([]);
    }
  };

  const handleProcess = () => {
    if (file) {
      uploadMutation.mutate(file);
    }
  };

  const handleAnalyze = () => {
    if (uploadSuccess?.fonte) {
      analisarMutation.mutate(uploadSuccess.fonte);
    }
  };

  return (
    <AppLayout 
      title="Inserir Conversas" 
      subtitle="Envie lotes de conversas em formato JSON ou CSV para processamento. A classificação de sentimentos será computada na sequência."
    >
      <section className="grid grid-cols-1 gap-gutter-desktop items-start">
        <div className="flex flex-col gap-space-md">
          
          {!file && (
            <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-space-lg flex flex-col shadow-sm">
              <div className="flex items-center justify-between mb-space-sm">
                <span className="font-label-md text-label-md font-semibold text-on-surface flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">cloud_upload</span>
                  Upload de Lote
                </span>
                <span className="text-label-sm font-label-sm px-2.5 py-0.5 rounded-full bg-surface-container text-primary font-medium">Lotes até 50MB</span>
              </div>
              
              <div 
                className="border-2 border-dashed border-outline-variant rounded-xl bg-surface p-space-xl flex flex-col items-center justify-center text-center hover:border-primary hover:bg-surface-container-low transition-all duration-200 cursor-pointer min-h-[260px]"
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input 
                  type="file" 
                  accept=".json,.csv" 
                  className="hidden" 
                  ref={fileInputRef} 
                  onChange={handleFileChange} 
                />
                <div className="w-16 h-16 rounded-full bg-surface-container-high flex items-center justify-center text-primary mb-space-md shadow-sm pointer-events-none">
                  <span className="material-symbols-outlined text-3xl">upload_file</span>
                </div>
                <h2 className="font-headline-sm text-headline-sm font-semibold text-on-surface mb-1 pointer-events-none">
                  Arraste seu arquivo aqui ou clique para selecionar
                </h2>
                <p className="font-body-sm text-body-sm text-on-surface-variant max-w-sm mb-space-md pointer-events-none">
                  Suporte para arquivos .JSON e .CSV (UTF-8)
                </p>
                <button 
                  className="inline-flex items-center gap-2 px-space-md py-2 rounded-lg bg-primary-container text-on-primary font-label-md text-label-md hover:bg-primary transition-all duration-150 active:scale-95 shadow-sm"
                  type="button"
                >
                  <span className="material-symbols-outlined text-lg">folder_open</span>
                  Selecionar Arquivo
                </button>
              </div>
            </div>
          )}

          {file && !uploadSuccess && (
            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-space-lg shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-headline-sm text-headline-sm font-semibold text-on-surface flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">task_alt</span>
                  Lote Preparado
                </h2>
                <button className="text-error font-label-sm px-2 py-1 hover:bg-red-50 rounded" onClick={() => setFile(null)}>
                  Cancelar
                </button>
              </div>
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-space-lg border-t border-outline-variant pt-4">
                <div className="flex items-start gap-space-md">
                  <div className="w-12 h-12 rounded-xl bg-surface-container-low border border-outline-variant flex items-center justify-center text-primary shrink-0">
                    <span className="material-symbols-outlined text-2xl">description</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="font-headline-sm text-headline-sm font-bold text-on-surface font-mono">{file.name}</span>
                    <p className="text-body-sm text-on-surface-variant mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <button 
                    onClick={handleProcess}
                    disabled={uploadMutation.isPending}
                    className="inline-flex items-center gap-2 px-space-lg py-2.5 rounded-lg bg-primary-container hover:bg-primary text-on-primary font-label-md text-label-md font-semibold transition-all shadow-sm disabled:opacity-50"
                  >
                    <span className="material-symbols-outlined text-xl">{uploadMutation.isPending ? 'sync' : 'upload'}</span>
                    {uploadMutation.isPending ? 'Importando...' : 'Fazer Upload'}
                  </button>
                </div>
              </div>

              {uploadError && (
                <div className="mt-4 p-4 bg-error-container text-on-error-container rounded-lg">
                  <div className="font-semibold">{uploadError}</div>
                  {uploadDetails.length > 0 && (
                    <ul className="mt-2 list-disc list-inside text-sm font-mono max-h-40 overflow-y-auto custom-scrollbar">
                      {uploadDetails.map((det, idx) => (
                        <li key={idx}>{det}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          )}

          {uploadSuccess && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-space-lg shadow-sm">
              <div className="flex items-center gap-2 text-emerald-800 mb-4">
                <span className="material-symbols-outlined text-emerald-600">check_circle</span>
                <h2 className="font-headline-sm font-semibold">Upload Concluído</h2>
              </div>
              <p className="text-emerald-700 text-body-md mb-2">
                O arquivo <strong>{file?.name}</strong> (fonte: {uploadSuccess.fonte}) foi importado com sucesso.
              </p>
              <ul className="list-disc list-inside text-emerald-700 text-body-sm mb-6">
                <li>Conversas importadas: {uploadSuccess.conversas}</li>
                <li>Mensagens processadas e anonimizadas: {uploadSuccess.mensagens}</li>
              </ul>
              
              {!analysisSuccess ? (
                <div className="border-t border-emerald-200 pt-4 flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-emerald-800">Classificação Pendente</h3>
                    <p className="text-sm text-emerald-700">As mensagens ainda não têm sentimento atribuído.</p>
                  </div>
                  <button 
                    onClick={handleAnalyze}
                    disabled={analisarMutation.isPending}
                    className="inline-flex items-center gap-2 px-space-lg py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-label-md text-label-md font-semibold transition-all disabled:opacity-50 shadow-sm"
                  >
                    <span className="material-symbols-outlined text-xl">{analisarMutation.isPending ? 'sync' : 'bolt'}</span>
                    {analisarMutation.isPending ? 'Classificando via BERT...' : 'Classificar com IA'}
                  </button>
                </div>
              ) : (
                <div className="border-t border-emerald-200 pt-4">
                  <h3 className="font-semibold text-emerald-800 flex items-center gap-2">
                    <span className="material-symbols-outlined">auto_awesome</span>
                    Classificação Finalizada
                  </h3>
                  <p className="text-sm text-emerald-700 mt-1">
                    Foram classificadas {analysisSuccess.mensagens_classificadas} mensagens utilizando o modelo <strong>{analysisSuccess.modelo_utilizado}</strong>.
                  </p>
                  <button 
                    onClick={() => {
                      setFile(null);
                      setUploadSuccess(null);
                      setAnalysisSuccess(null);
                    }}
                    className="mt-4 px-4 py-2 bg-emerald-100 text-emerald-800 rounded font-medium hover:bg-emerald-200 transition-colors"
                  >
                    Fazer novo upload
                  </button>
                </div>
              )}
            </div>
          )}

        </div>
      </section>
    </AppLayout>
  );
}

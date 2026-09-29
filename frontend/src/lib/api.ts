import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

// --- Tipagens Extraídas da API ---
export type Role = "ADMIN" | "USER";
export type Sentimento = "positivo" | "negativo" | "neutro";
export type Modelo = "lexico" | "classico" | "bertimbau";

export interface LoginResponse {
  email: string;
  access_token: string;
  refresh_token: string;
}

export interface RegisterResponse {
  name: string;
  email: string;
  role: Role;
  created_at: string;
}

export interface UploadResponse {
  fonte: string;
  conversas: number;
  mensagens: number;
  status: "importado";
}

export interface AnalisarResponse {
  fonte: string;
  total_conversas: number;
  mensagens_classificadas: number;
  modelo_utilizado: Modelo;
}

export interface Indicadores {
  abertura: Sentimento;
  encerramento: Sentimento;
  delta: number;
  trocas_de_polaridade: number;
  pior_momento: number;
  n_mensagens: number;
}

export interface ConversaListItem {
  id: number;
  origem_id: string;
  fonte: string;
  indicadores: Indicadores | null;
}

export interface Mensagem {
  ordem: number;
  autor: string;
  texto: string;
  rotulo: Sentimento | null;
  score: number | null;
  rotulo_real: Sentimento | null;
}

export interface ConversaDetalhe extends ConversaListItem {
  mensagens: Mensagem[];
}

export interface MatrizModelo {
  nome: Modelo;
  f1_macro: number;
  matriz: number[][]; 
}

export interface McNemarComparacao {
  a: Modelo;
  b: Modelo;
  acertos_so_de_a: number;
  acertos_so_de_b: number;
  p: number;
  significativo: boolean;
}

export interface MetricasResponse {
  distribuicao: Record<Sentimento, number>;
  total_conversas: number;
  modelos: {
    n_teste: number;
    modelos: MatrizModelo[];
    mcnemar: McNemarComparacao[];
  } | null;
}

export interface ApiErro {
  erro: string | string[];
  detalhes?: string[];
}

export interface PaginatedResponse<T> {
  total: number;
  conversas: T[];
}

export type ConversaListResponse = PaginatedResponse<ConversaListItem>;

// --- Configuração do Axios ---
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export const api = axios.create({
  baseURL: BASE_URL,
});

// Interceptor para injetar o Access Token
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
}, (error) => Promise.reject(error));

// Interceptor para tratar 401 e fazer Refresh do Token
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErro>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          throw new Error('No refresh token available');
        }

        const res = await axios.post<{ access_token: string; refresh_token: string }>(
          `${BASE_URL}/refresh`,
          { refresh_token: refreshToken }
        );

        localStorage.setItem('access_token', res.data.access_token);
        localStorage.setItem('refresh_token', res.data.refresh_token);

        originalRequest.headers.Authorization = `Bearer ${res.data.access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        if (typeof window !== 'undefined') {
          // eslint-disable-next-line @next/next/no-location-assign-relative-destination
          window.location.href = '/login'; // Redireciona via JS puro para não depender do router no lib
        }
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

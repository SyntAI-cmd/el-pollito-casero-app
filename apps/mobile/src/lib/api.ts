import Constants from 'expo-constants';
import { Platform } from 'react-native';

/**
 * URL base de la API. En desarrollo se toma de EXPO_PUBLIC_API_URL; si falta, en Android
 * se usa la IP de la PC que expone Metro (un celular no llega a "localhost" de la PC).
 */
export function apiBaseUrl(): string {
  const configurada = process.env.EXPO_PUBLIC_API_URL;
  if (configurada) return configurada.replace(/\/$/, '');
  if (Platform.OS === 'web') return 'http://localhost:8000';
  const host = Constants.expoConfig?.hostUri?.split(':')[0];
  return host ? `http://${host}:8000` : 'http://localhost:8000';
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function apiGet<T>(ruta: string): Promise<T> {
  const respuesta = await fetch(`${apiBaseUrl()}${ruta}`);
  if (!respuesta.ok) throw new ApiError(respuesta.status, `Error ${respuesta.status} en ${ruta}`);
  return (await respuesta.json()) as T;
}

export interface Salud {
  estado: string;
  entorno: string;
  version: string;
}

export const consultarSalud = () => apiGet<Salud>('/health');

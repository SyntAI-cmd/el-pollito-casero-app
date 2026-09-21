import type { components, paths } from '@pollito/api-client';
import Constants from 'expo-constants';
import createClient, { type Middleware } from 'openapi-fetch';
import { Platform } from 'react-native';

import { useSesion } from '@/stores/sesion';

export type Esquemas = components['schemas'];
export type Pedido = Esquemas['PedidoSalida'];
export type ItemPedido = Esquemas['ItemSalida'];
export type Cliente = Esquemas['ClienteSalida'];
export type Salida = Esquemas['SalidaSalida'];
export type Producto = Esquemas['ProductoSalida'];
export type Usuario = Esquemas['UsuarioSalida'];
export type Cajon = Esquemas['CajonSalida'];
export type NotaDelDia = Esquemas['NotaDelDia'];
export type PrecioResuelto = Esquemas['PrecioResuelto'];
export type EstadoPedido = Esquemas['Estado'];

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

export function wsUrl(token: string): string {
  return `${apiBaseUrl().replace(/^http/, 'ws')}/ws?token=${encodeURIComponent(token)}`;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly codigo: string = 'error',
  ) {
    super(message);
  }

  /** Un error de validación o permiso no se reintenta: se muestra. Solo la red se reintenta. */
  get esDeRed(): boolean {
    return this.status === 0;
  }
}

let refrescando: Promise<boolean> | null = null;

/** Un solo refresh en vuelo aunque fallen varias llamadas a la vez. */
async function refrescarSesion(): Promise<boolean> {
  if (!refrescando) {
    refrescando = (async () => {
      const { refresh } = useSesion.getState();
      if (!refresh) return false;
      try {
        const respuesta = await fetch(`${apiBaseUrl()}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh }),
        });
        if (!respuesta.ok) {
          await useSesion.getState().cerrar();
          return false;
        }
        const datos = (await respuesta.json()) as Esquemas['TokensSalida'];
        await useSesion.getState().iniciar(datos);
        return true;
      } catch {
        return false;
      } finally {
        refrescando = null;
      }
    })();
  }
  return refrescando;
}

const autenticacion: Middleware = {
  async onRequest({ request }) {
    const token = useSesion.getState().acceso;
    if (token && !request.headers.has('Authorization')) {
      request.headers.set('Authorization', `Bearer ${token}`);
    }
    return request;
  },
  async onResponse({ request, response }) {
    // Sin cambios se devuelve undefined: openapi-fetch exige que lo que se devuelva sea
    // `instanceof Response`, y en React Native la respuesta de fetch no siempre lo es.
    if (response.status !== 401 || request.url.includes('/auth/')) return undefined;
    if (!(await refrescarSesion())) return undefined;
    const reintento = new Request(request, {
      headers: new Headers(request.headers),
    });
    reintento.headers.set('Authorization', `Bearer ${useSesion.getState().acceso}`);
    const respuesta = await fetch(reintento);
    // Se reconstruye con el constructor global por el mismo motivo de arriba.
    return new Response(await respuesta.arrayBuffer(), {
      status: respuesta.status,
      statusText: respuesta.statusText,
      headers: respuesta.headers,
    });
  },
};

export const api = createClient<paths>({ baseUrl: apiBaseUrl() });
api.use(autenticacion);

interface CuerpoError {
  codigo?: string;
  mensaje?: string;
  detail?: unknown;
}

/** Convierte la respuesta de openapi-fetch en dato o ApiError con el mensaje del servidor. */
export function desenvolver<T>(resultado: { data?: T; error?: unknown; response: Response }): T {
  if (resultado.error !== undefined || !resultado.response.ok) {
    const cuerpo = (resultado.error ?? {}) as CuerpoError;
    const mensaje =
      cuerpo.mensaje ??
      (typeof cuerpo.detail === 'string' ? cuerpo.detail : null) ??
      `Error ${resultado.response.status}`;
    throw new ApiError(resultado.response.status, mensaje, cuerpo.codigo);
  }
  return resultado.data as T;
}

export function mensajeDeError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return 'Sin conexión con el servidor';
  if (error instanceof Error) return error.message;
  return 'Algo salió mal';
}

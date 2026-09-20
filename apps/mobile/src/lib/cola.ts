import { create } from 'zustand';

import * as almacen from '@/lib/almacen';
import { ApiError, apiBaseUrl } from '@/lib/api';
import { useSesion } from '@/stores/sesion';

/**
 * Cola de mutaciones para trabajar sin señal. Cada operación lleva una id generada acá; el
 * servidor ignora duplicados por esa id. Se reintenta en orden y se frena en el primer fallo de
 * red para no desordenar (pesar antes de cargar, por ejemplo). Un 4xx no se reintenta: queda
 * marcado con su mensaje para que el usuario lo vea y lo descarte.
 */
export interface Mutacion {
  id: string;
  descripcion: string; // "Cajón 20,3 kg · #00012"
  metodo: 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  ruta: string;
  cuerpo: unknown;
  creadaEn: number;
  intentos: number;
  error: string | null; // fijado cuando el servidor la rechazó (no se reintenta)
  claveQuery?: readonly unknown[]; // qué invalidar cuando se confirme
}

interface EstadoCola {
  pendientes: Mutacion[];
  procesando: boolean;
  cargada: boolean;
  cargar: () => Promise<void>;
  encolar: (m: Omit<Mutacion, 'creadaEn' | 'intentos' | 'error'>) => Promise<void>;
  descartar: (id: string) => Promise<void>;
  procesar: (alConfirmar?: (m: Mutacion, respuesta: unknown) => void) => Promise<void>;
}

const CLAVE = 'cola.mutaciones';

async function ejecutar(m: Mutacion): Promise<unknown> {
  const respuesta = await fetch(`${apiBaseUrl()}${m.ruta}`, {
    method: m.metodo,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${useSesion.getState().acceso ?? ''}`,
    },
    body: m.cuerpo === undefined ? undefined : JSON.stringify(m.cuerpo),
  });
  if (!respuesta.ok) {
    let mensaje = `Error ${respuesta.status}`;
    try {
      const cuerpo = (await respuesta.json()) as { mensaje?: string };
      mensaje = cuerpo.mensaje ?? mensaje;
    } catch {
      /* sin cuerpo JSON */
    }
    throw new ApiError(respuesta.status, mensaje);
  }
  return respuesta.status === 204 ? null : respuesta.json();
}

export const useCola = create<EstadoCola>((set, get) => ({
  pendientes: [],
  procesando: false,
  cargada: false,
  cargar: async () => {
    const guardadas = (await almacen.leer<Mutacion[]>(CLAVE)) ?? [];
    set({ pendientes: guardadas, cargada: true });
  },
  encolar: async (m) => {
    const nueva: Mutacion = { ...m, creadaEn: Date.now(), intentos: 0, error: null };
    const pendientes = [...get().pendientes, nueva];
    set({ pendientes });
    await almacen.guardar(CLAVE, pendientes);
  },
  descartar: async (id) => {
    const pendientes = get().pendientes.filter((m) => m.id !== id);
    set({ pendientes });
    await almacen.guardar(CLAVE, pendientes);
  },
  procesar: async (alConfirmar) => {
    if (get().procesando) return;
    set({ procesando: true });
    try {
      for (const m of [...get().pendientes]) {
        if (m.error) continue; // rechazada por el servidor: espera que el usuario la descarte
        try {
          const respuesta = await ejecutar(m);
          const pendientes = get().pendientes.filter((x) => x.id !== m.id);
          set({ pendientes });
          await almacen.guardar(CLAVE, pendientes);
          alConfirmar?.(m, respuesta);
        } catch (error) {
          if (error instanceof ApiError && error.status === 401) break; // sesión: se reintenta luego
          if (error instanceof ApiError) {
            const pendientes = get().pendientes.map((x) =>
              x.id === m.id ? { ...x, error: error.message, intentos: x.intentos + 1 } : x,
            );
            set({ pendientes });
            await almacen.guardar(CLAVE, pendientes);
            continue;
          }
          break; // sin red: se frena acá y se reintenta en orden cuando vuelva la conexión
        }
      }
    } finally {
      set({ procesando: false });
    }
  },
}));

export const cantidadPendientes = () =>
  useCola.getState().pendientes.filter((m) => !m.error).length;

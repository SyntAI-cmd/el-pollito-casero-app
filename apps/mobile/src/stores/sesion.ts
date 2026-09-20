import { Platform } from 'react-native';
import { create } from 'zustand';

import type { Esquemas } from '@/lib/api';

export type Rol = 'admin' | 'preventista' | 'cobrador' | 'cliente';

type Tokens = Esquemas['TokensSalida'];

interface Sesion {
  acceso: string | null;
  refresh: string | null;
  usuario: Esquemas['UsuarioSalida'] | null;
  lista: boolean; // ya se leyó el almacenamiento seguro
  iniciar: (tokens: Tokens) => Promise<void>;
  cerrar: () => Promise<void>;
  restaurar: () => Promise<void>;
}

const CLAVE = 'pollito.sesion';

/** SecureStore en el celular; en el navegador no existe y se usa localStorage. */
const almacen = {
  async leer(): Promise<string | null> {
    if (Platform.OS === 'web') {
      try {
        return globalThis.localStorage?.getItem(CLAVE) ?? null;
      } catch {
        return null;
      }
    }
    const SecureStore = await import('expo-secure-store');
    return SecureStore.getItemAsync(CLAVE);
  },
  async guardar(valor: string | null): Promise<void> {
    if (Platform.OS === 'web') {
      try {
        if (valor === null) globalThis.localStorage?.removeItem(CLAVE);
        else globalThis.localStorage?.setItem(CLAVE, valor);
      } catch {
        /* modo privado o sin almacenamiento: la sesión dura lo que dura la pestaña */
      }
      return;
    }
    const SecureStore = await import('expo-secure-store');
    if (valor === null) await SecureStore.deleteItemAsync(CLAVE);
    else await SecureStore.setItemAsync(CLAVE, valor);
  },
};

export const useSesion = create<Sesion>((set) => ({
  acceso: null,
  refresh: null,
  usuario: null,
  lista: false,
  iniciar: async (tokens) => {
    set({ acceso: tokens.acceso, refresh: tokens.refresh, usuario: tokens.usuario, lista: true });
    await almacen.guardar(JSON.stringify(tokens));
  },
  cerrar: async () => {
    set({ acceso: null, refresh: null, usuario: null, lista: true });
    await almacen.guardar(null);
  },
  restaurar: async () => {
    try {
      const crudo = await almacen.leer();
      if (crudo) {
        const tokens = JSON.parse(crudo) as Tokens;
        set({ acceso: tokens.acceso, refresh: tokens.refresh, usuario: tokens.usuario });
      }
    } finally {
      set({ lista: true });
    }
  },
}));

export const rolActual = () => useSesion.getState().usuario?.rol ?? null;

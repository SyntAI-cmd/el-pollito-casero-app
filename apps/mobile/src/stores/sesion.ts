import { create } from 'zustand';

export type Rol = 'admin' | 'preventista' | 'cobrador' | 'cliente';

interface Sesion {
  token: string | null;
  rol: Rol | null;
  nombre: string | null;
  iniciar: (datos: { token: string; rol: Rol; nombre: string }) => void;
  cerrar: () => void;
}

/** Sesión en memoria. La persistencia segura (expo-secure-store) llega con el módulo auth. */
export const useSesion = create<Sesion>((set) => ({
  token: null,
  rol: null,
  nombre: null,
  iniciar: ({ token, rol, nombre }) => set({ token, rol, nombre }),
  cerrar: () => set({ token: null, rol: null, nombre: null }),
}));

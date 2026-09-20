import { Redirect } from 'expo-router';

import { useSesion } from '@/stores/sesion';

/** Puerta de entrada: manda a cada rol a su grupo de rutas. */
export default function Entrada() {
  const rol = useSesion((s) => s.usuario?.rol ?? null);
  if (!rol) return <Redirect href="/login" />;
  if (rol === 'preventista') return <Redirect href="/(reparto)" />;
  if (rol === 'cobrador') return <Redirect href="/(cobrador)" />;
  return <Redirect href="/(admin)" />;
}

import * as Location from 'expo-location';
import { create } from 'zustand';

import { api } from '@/lib/api';

/**
 * El repartidor comparte GPS mientras dura la salida: cada 15 segundos o cada 25 metros.
 * Es un watch en primer plano (la app abierta); el modo en segundo plano requiere un build
 * de desarrollo con el permiso de ubicación en background, que no entra en esta fase.
 */
interface EstadoGps {
  salidaId: string | null;
  ultimaEnvio: number | null;
  error: string | null;
  compartir: (salidaId: string) => Promise<void>;
  detener: () => void;
}

let suscripcion: Location.LocationSubscription | null = null;

export const useGps = create<EstadoGps>((set, get) => ({
  salidaId: null,
  ultimaEnvio: null,
  error: null,
  compartir: async (salidaId) => {
    const permiso = await Location.requestForegroundPermissionsAsync();
    if (permiso.status !== 'granted') {
      set({ error: 'Sin permiso de ubicación' });
      return;
    }
    get().detener();
    suscripcion = await Location.watchPositionAsync(
      { accuracy: Location.Accuracy.High, timeInterval: 15_000, distanceInterval: 25 },
      async (posicion) => {
        const { error } = await api.POST('/salidas/{salida_id}/ubicacion', {
          params: { path: { salida_id: salidaId } },
          body: {
            lat: posicion.coords.latitude.toFixed(6),
            lng: posicion.coords.longitude.toFixed(6),
            velocidad:
              posicion.coords.speed != null && posicion.coords.speed >= 0
                ? (posicion.coords.speed * 3.6).toFixed(2)
                : null,
            registrado_en: new Date(posicion.timestamp).toISOString(),
          },
        });
        set({ ultimaEnvio: error ? get().ultimaEnvio : Date.now() });
      },
    );
    set({ salidaId, error: null });
  },
  detener: () => {
    suscripcion?.remove();
    suscripcion = null;
    set({ salidaId: null });
  },
}));

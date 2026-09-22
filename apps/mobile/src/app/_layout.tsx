import '../global.css';

import {
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
  Inter_800ExtraBold,
  useFonts,
} from '@expo-google-fonts/inter';
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import * as Network from 'expo-network';
import { Stack, useRouter, useSegments } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { AppState } from 'react-native';

import { ApiError } from '@/lib/api';
import { useCola } from '@/lib/cola';
import { useTiempoReal } from '@/lib/consultas';
import { registrarPush } from '@/lib/push';
import { useSesion } from '@/stores/sesion';
import { tokens } from '@/theme/tokens';

SplashScreen.preventAutoHideAsync();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Solo se reintenta la red. Un 401 (sesión vencida) o un 4xx se muestran: reintentarlos
      // dispara otra vuelta de refresh y deja la app dando vueltas en lugar de ir al login.
      retry: (intentos, error) =>
        error instanceof ApiError ? error.esDeRed && intentos < 1 : intentos < 1,
      staleTime: 15_000,
    },
  },
});

/** Vive dentro del QueryClientProvider: cola offline, red y canal en tiempo real. */
function Infraestructura() {
  const cliente = useQueryClient();
  const cargarCola = useCola((s) => s.cargar);
  const procesar = useCola((s) => s.procesar);
  const token = useSesion((s) => s.acceso);

  useEffect(() => {
    cargarCola();
  }, [cargarCola]);

  useEffect(() => {
    if (token) registrarPush();
  }, [token]);

  useEffect(() => {
    if (!token) return;
    const intentar = () =>
      procesar((m) => {
        if (m.claveQuery) cliente.invalidateQueries({ queryKey: m.claveQuery });
      });
    intentar();
    const suscripcion = Network.addNetworkStateListener((estado) => {
      if (estado.isConnected) intentar();
    });
    const app = AppState.addEventListener('change', (estado) => {
      if (estado === 'active') intentar();
    });
    const cada = setInterval(intentar, 30_000);
    return () => {
      suscripcion.remove();
      app.remove();
      clearInterval(cada);
    };
  }, [token, procesar, cliente]);

  useTiempoReal();
  return null;
}

export default function RootLayout() {
  const [fuentesListas] = useFonts({
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
    Inter_800ExtraBold,
  });
  const sesionLista = useSesion((s) => s.lista);
  const restaurar = useSesion((s) => s.restaurar);
  const usuario = useSesion((s) => s.usuario);
  const router = useRouter();
  const segmentos = useSegments();

  useEffect(() => {
    restaurar();
  }, [restaurar]);

  /**
   * Cuando se cae la sesión (vence el refresh, la revocan, se reinicia el servidor) el envío al
   * login se decide en un solo lugar. Si además lo decidiera cada grupo de rutas, las pantallas
   * que quedan montadas se redirigen entre sí en cada render y la app se cuelga.
   */
  useEffect(() => {
    if (!sesionLista || usuario) return;
    if (segmentos[0] !== 'login') router.replace('/login');
  }, [sesionLista, usuario, segmentos, router]);

  useEffect(() => {
    if (fuentesListas && sesionLista) SplashScreen.hideAsync();
  }, [fuentesListas, sesionLista]);

  if (!fuentesListas || !sesionLista) return null;

  return (
    <QueryClientProvider client={queryClient}>
      <Infraestructura />
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: tokens.colors.charcoal },
          headerTintColor: '#FFFFFF',
          headerTitleStyle: { fontFamily: 'Inter_700Bold' },
          contentStyle: { backgroundColor: tokens.colors.background },
        }}>
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="login" options={{ headerShown: false }} />
        <Stack.Screen name="(reparto)" options={{ headerShown: false }} />
        <Stack.Screen name="(cobrador)" options={{ headerShown: false }} />
        <Stack.Screen name="(admin)" options={{ headerShown: false }} />
      </Stack>
    </QueryClientProvider>
  );
}

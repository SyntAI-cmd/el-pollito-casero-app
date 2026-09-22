import { Redirect, Tabs } from 'expo-router';

import { NavFlotante } from '@/components/NavFlotante';
import { useSesion } from '@/stores/sesion';
import { tokens } from '@/theme/tokens';

const ITEMS = [
  { nombre: 'index', etiqueta: 'Reparto', icono: 'truck-delivery' as const },
  { nombre: 'entregas', etiqueta: 'Entregas', icono: 'package-variant' as const },
  { nombre: 'pesada/index', etiqueta: 'Balanza', icono: 'scale' as const },
  { nombre: 'carga', etiqueta: 'Carga', icono: 'truck-check' as const },
];

export default function LayoutReparto() {
  const rol = useSesion((s) => s.usuario?.rol ?? null);
  if (!rol) return null; // sin sesión manda el layout raíz, para no redirigir de a dos
  if (rol !== 'preventista' && rol !== 'admin') return <Redirect href="/" />;
  return (
    <Tabs
      tabBar={(props) => (
        <NavFlotante
          props={props}
          items={ITEMS}
          fab={{ etiqueta: 'Cargar pedido', href: '/(reparto)/nuevo-pedido' }}
        />
      )}
      screenOptions={{
        headerStyle: { backgroundColor: tokens.colors.charcoal },
        headerTintColor: '#FFFFFF',
        headerTitleStyle: { fontFamily: 'Inter_700Bold' },
        sceneStyle: { backgroundColor: tokens.colors.background },
      }}>
      <Tabs.Screen name="index" options={{ title: 'Reparto' }} />
      <Tabs.Screen name="entregas" options={{ title: 'Mis entregas' }} />
      <Tabs.Screen name="pesada/index" options={{ title: 'Balanza' }} />
      <Tabs.Screen name="carga" options={{ title: 'Carga del camión' }} />
      <Tabs.Screen name="nuevo-pedido" options={{ title: 'Cargar pedido', href: null }} />
      <Tabs.Screen name="entrega/[id]" options={{ title: 'Entrega', href: null }} />
      <Tabs.Screen name="pesada/[id]" options={{ title: 'Pesada', href: null }} />
    </Tabs>
  );
}

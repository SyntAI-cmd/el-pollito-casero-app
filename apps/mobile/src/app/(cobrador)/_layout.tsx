import { Redirect, Tabs } from 'expo-router';

import { NavFlotante } from '@/components/NavFlotante';
import { useSesion } from '@/stores/sesion';
import { tokens } from '@/theme/tokens';

const ITEMS = [
  { nombre: 'index', etiqueta: 'Cuentas', icono: 'account-cash' as const },
  { nombre: 'caja', etiqueta: 'Caja', icono: 'cash-register' as const },
];

export default function LayoutCobrador() {
  const rol = useSesion((s) => s.usuario?.rol ?? null);
  if (rol !== 'cobrador' && rol !== 'admin') return <Redirect href="/" />;
  return (
    <Tabs
      tabBar={(props) => <NavFlotante props={props} items={ITEMS} />}
      screenOptions={{
        headerStyle: { backgroundColor: tokens.colors.charcoal },
        headerTintColor: '#FFFFFF',
        headerTitleStyle: { fontFamily: 'Inter_700Bold' },
        sceneStyle: { backgroundColor: tokens.colors.background },
      }}>
      <Tabs.Screen name="index" options={{ title: 'Cuentas a cobrar' }} />
      <Tabs.Screen name="caja" options={{ title: 'Mi caja' }} />
      <Tabs.Screen name="cobrar/[id]" options={{ title: 'Cobrar', href: null }} />
    </Tabs>
  );
}

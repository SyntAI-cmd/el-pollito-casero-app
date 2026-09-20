import { Redirect, Stack } from 'expo-router';

import { useSesion } from '@/stores/sesion';
import { tokens } from '@/theme/tokens';

export default function LayoutCobrador() {
  const rol = useSesion((s) => s.usuario?.rol ?? null);
  if (rol !== 'cobrador' && rol !== 'admin') return <Redirect href="/" />;
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: tokens.colors.charcoal },
        headerTintColor: '#FFFFFF',
        headerTitleStyle: { fontFamily: 'Inter_700Bold' },
        contentStyle: { backgroundColor: tokens.colors.background },
      }}
    />
  );
}

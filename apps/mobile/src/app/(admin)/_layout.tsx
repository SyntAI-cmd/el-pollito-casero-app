import { Redirect, Stack } from 'expo-router';

import { useSesion } from '@/stores/sesion';
import { tokens } from '@/theme/tokens';

export default function LayoutAdmin() {
  const rol = useSesion((s) => s.usuario?.rol ?? null);
  if (rol !== 'admin') return <Redirect href="/" />;
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

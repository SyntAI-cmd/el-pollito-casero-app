import '../global.css';

import {
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
  Inter_800ExtraBold,
  useFonts,
} from '@expo-google-fonts/inter';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';

import { tokens } from '@/theme/tokens';

SplashScreen.preventAutoHideAsync();

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 10_000 } },
});

export default function RootLayout() {
  const [fuentesListas] = useFonts({
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
    Inter_800ExtraBold,
  });

  useEffect(() => {
    if (fuentesListas) SplashScreen.hideAsync();
  }, [fuentesListas]);

  if (!fuentesListas) return null;

  return (
    <QueryClientProvider client={queryClient}>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: tokens.colors.charcoal },
          headerTintColor: '#FFFFFF',
          headerTitleStyle: { fontFamily: 'Inter_700Bold' },
          contentStyle: { backgroundColor: tokens.colors.background },
        }}
      />
    </QueryClientProvider>
  );
}

import { Stack } from 'expo-router';
import { ScrollView, Text, View } from 'react-native';

import { EstadoApi } from '@/components/EstadoApi';

export default function Inicio() {
  return (
    <>
      <Stack.Screen options={{ title: 'Pollito Casero' }} />
      <ScrollView
        className="flex-1 bg-background"
        contentContainerClassName="p-gutter pb-nav-safe gap-4 web:w-full web:max-w-[1280px] web:self-center">
        <View className="rounded-panel bg-charcoal p-6">
          <Text className="font-bold text-[11px] uppercase tracking-[0.06em] text-white/70">
            Fase 0 · base del sistema
          </Text>
          <Text className="mt-2 font-extrabold text-[32px] leading-[36px] tracking-[-0.02em] text-white">
            Pollito Casero
          </Text>
          <Text className="mt-2 font-sans text-[16px] text-white/80">
            Reparto mayorista · San Martín, Mendoza
          </Text>
        </View>
        <EstadoApi />
        <View className="rounded-card border border-border bg-surface p-4">
          <Text className="font-bold text-[18px] text-on-surface">Qué sigue</Text>
          <Text className="mt-2 font-sans text-[14px] text-on-surface-v">
            Todavía no hay pedidos, clientes ni pesadas: llegan con las fases 1 a 3. Esta pantalla
            existe solo para comprobar que la app y la API se hablan.
          </Text>
        </View>
      </ScrollView>
    </>
  );
}

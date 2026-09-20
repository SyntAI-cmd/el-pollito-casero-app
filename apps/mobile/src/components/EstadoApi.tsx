import { useQuery } from '@tanstack/react-query';
import { Text, View } from 'react-native';

import { apiBaseUrl, consultarSalud } from '@/lib/api';

/** Tarjeta de diagnóstico de la Fase 0: muestra si la app llega a la API. */
export function EstadoApi() {
  const { data, error } = useQuery({ queryKey: ['salud'], queryFn: consultarSalud });

  let etiqueta = 'Consultando…';
  let colorTexto = 'text-pending';
  let icono = '◌';
  if (data) {
    etiqueta = `API conectada · ${data.entorno} · v${data.version}`;
    colorTexto = 'text-success';
    icono = '✓';
  } else if (error) {
    etiqueta = 'Sin conexión con la API';
    colorTexto = 'text-danger';
    icono = '✕';
  }

  return (
    <View
      className="rounded-card border border-border bg-surface p-4"
      accessibilityRole="summary"
      accessibilityLabel={etiqueta}>
      <Text className="font-bold text-[11px] uppercase tracking-[0.06em] text-on-surface-v">
        Estado del sistema
      </Text>
      <Text className={`mt-2 font-bold text-[16px] ${colorTexto}`} testID="estado-api">
        {icono} {etiqueta}
      </Text>
      <Text
        className="mt-1 font-sans text-[14px] text-on-surface-v"
        style={{ fontVariant: ['tabular-nums'] }}>
        {apiBaseUrl()}
      </Text>
    </View>
  );
}

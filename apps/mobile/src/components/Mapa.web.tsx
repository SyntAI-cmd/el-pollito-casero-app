import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Linking, Pressable, View } from 'react-native';

import { Texto } from '@/components/ui/Texto';
import { tokens } from '@/theme/tokens';

import type { Punto } from './Mapa';

export type { Punto } from './Mapa';

/**
 * En el navegador react-native-maps no existe. Se muestra un iframe de Google Maps (embed sin
 * API key, solo búsqueda) con el primer punto; el mapa en vivo de administración llega en la
 * Fase 6 con la key del servidor.
 */
export function Mapa({
  puntos,
  alto = 240,
}: {
  puntos: Punto[];
  recorrido?: Punto[];
  alto?: number;
}) {
  const centro = puntos[0];
  if (!centro) {
    return (
      <View
        className="items-center justify-center rounded-card border border-border bg-surface"
        style={{ height: alto }}>
        <MaterialCommunityIcons name="map-marker-off" size={32} color={tokens.colors.pending} />
        <Texto variante="body-md" tono="suave">
          Sin coordenadas
        </Texto>
      </View>
    );
  }
  const src = `https://maps.google.com/maps?q=${centro.lat},${centro.lng}&z=15&output=embed`;
  return (
    <View className="overflow-hidden rounded-card border border-border" style={{ height: alto }}>
      <iframe
        title="Mapa"
        src={src}
        style={{ border: 0, width: '100%', height: '100%' }}
        loading="lazy"
      />
      <Pressable
        accessibilityRole="link"
        onPress={() =>
          Linking.openURL(
            `https://www.google.com/maps/search/?api=1&query=${centro.lat},${centro.lng}`,
          )
        }
        className="absolute bottom-2 right-2 h-12 flex-row items-center gap-1 rounded-pill bg-charcoal px-4">
        <MaterialCommunityIcons name="open-in-new" size={16} color="#FFFFFF" />
        <Texto variante="label-md" tono="claro">
          Abrir en Google Maps
        </Texto>
      </Pressable>
    </View>
  );
}

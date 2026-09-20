import { View } from 'react-native';
import MapView, { Marker, PROVIDER_GOOGLE, Polyline } from 'react-native-maps';

import { tokens } from '@/theme/tokens';

export interface Punto {
  lat: number;
  lng: number;
  titulo?: string;
  tipo?: 'parada' | 'camion' | 'destino';
}

/** Mapa embebido con Google Maps (react-native-maps). En web hay una versión aparte (Mapa.web.tsx). */
export function Mapa({
  puntos,
  recorrido,
  alto = 240,
}: {
  puntos: Punto[];
  recorrido?: Punto[];
  alto?: number;
}) {
  const centro = puntos[0] ?? recorrido?.[recorrido.length - 1] ?? { lat: -33.081, lng: -68.469 };
  return (
    <View className="overflow-hidden rounded-card" style={{ height: alto }}>
      <MapView
        provider={PROVIDER_GOOGLE}
        style={{ flex: 1 }}
        initialRegion={{
          latitude: centro.lat,
          longitude: centro.lng,
          latitudeDelta: 0.02,
          longitudeDelta: 0.02,
        }}>
        {puntos.map((p, i) => (
          <Marker
            key={`${p.lat},${p.lng},${i}`}
            coordinate={{ latitude: p.lat, longitude: p.lng }}
            title={p.titulo}
            pinColor={p.tipo === 'camion' ? tokens.colors.charcoal : tokens.colors.primary}
          />
        ))}
        {recorrido && recorrido.length > 1 ? (
          <Polyline
            coordinates={recorrido.map((p) => ({ latitude: p.lat, longitude: p.lng }))}
            strokeColor={tokens.colors.primary}
            strokeWidth={4}
          />
        ) : null}
      </MapView>
    </View>
  );
}

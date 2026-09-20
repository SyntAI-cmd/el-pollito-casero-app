import { useRouter } from 'expo-router';
import { Pressable, View } from 'react-native';

import { Badge } from '@/components/ui/Estado';
import { ErrorCarga, Pantalla, Vacio } from '@/components/ui/Pantalla';
import { Tarjeta } from '@/components/ui/Tarjeta';
import { kilosPesados, resumenProductos } from '@/components/ui/TarjetaPedido';
import { Texto } from '@/components/ui/Texto';
import { usePedidosDelDia } from '@/lib/consultas';
import { cajones, hoyIso, kilos } from '@/lib/formato';

/** Primero se elige el pedido; los que faltan pesar van arriba. */
export default function ElegirPedidoParaPesar() {
  const router = useRouter();
  const pedidos = usePedidosDelDia(hoyIso());
  const lista = [...(pedidos.data ?? [])]
    .filter((p) => p.estado === 'recibido' || p.estado === 'preparando')
    .sort(
      (a, b) =>
        Number(b.sin_pesar.length > 0) - Number(a.sin_pesar.length > 0) ||
        a.numero.localeCompare(b.numero),
    );

  return (
    <Pantalla refrescando={pedidos.isFetching} onRefrescar={() => pedidos.refetch()}>
      <View>
        <Texto variante="headline-lg">¿Qué pedido pesamos?</Texto>
        <Texto variante="body-md" tono="suave">
          Se pesa bruto; la balanza del sistema resta la tara y muestra el neto.
        </Texto>
      </View>
      {pedidos.isError && !pedidos.data ? (
        <ErrorCarga error={pedidos.error} onReintentar={() => pedidos.refetch()} />
      ) : null}
      {pedidos.data && lista.length === 0 ? (
        <Vacio
          icono="scale"
          titulo="Nada para pesar"
          detalle="Los pedidos de hoy ya salieron o no hay pedidos cargados."
        />
      ) : null}
      {lista.map((p) => (
        <Pressable
          key={p.id}
          accessibilityRole="button"
          onPress={() => router.push({ pathname: '/(reparto)/pesada/[id]', params: { id: p.id } })}>
          <Tarjeta>
            <View className="flex-row items-start justify-between gap-2">
              <View className="flex-1">
                <Texto variante="label-caps" tono="suave">
                  #{p.numero}
                </Texto>
                <Texto variante="headline-md" numberOfLines={1}>
                  {p.cliente_nombre}
                </Texto>
                <Texto variante="body-md" tono="suave" numberOfLines={2}>
                  {resumenProductos(p)}
                </Texto>
              </View>
              <Badge
                estado={p.sin_pesar.length ? 'pendiente' : 'preparando'}
                texto={p.sin_pesar.length ? `Faltan ${p.sin_pesar.length}` : 'Pesado'}
              />
            </View>
            <Texto variante="body-metric" className="mt-2">
              {cajones(p.cajones)} · {kilos(kilosPesados(p))}
            </Texto>
          </Tarjeta>
        </Pressable>
      ))}
    </Pantalla>
  );
}

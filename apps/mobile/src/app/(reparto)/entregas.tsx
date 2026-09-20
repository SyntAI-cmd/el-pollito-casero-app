import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { ErrorCarga, Pantalla, Vacio } from '@/components/ui/Pantalla';
import { TarjetaPedido } from '@/components/ui/TarjetaPedido';
import { Texto } from '@/components/ui/Texto';
import { usePedidosDelDia } from '@/lib/consultas';
import { hoyIso } from '@/lib/formato';

type Filtro = 'pendientes' | 'entregados' | 'todos';

const ORDEN = { en_camino: 0, preparando: 1, recibido: 2, entregado: 3, cancelado: 4 } as const;

export default function MisEntregas() {
  const router = useRouter();
  const [filtro, setFiltro] = useState<Filtro>('pendientes');
  const pedidos = usePedidosDelDia(hoyIso());
  const lista = [...(pedidos.data ?? [])]
    .filter((p) => p.estado !== 'cancelado')
    .filter((p) =>
      filtro === 'todos'
        ? true
        : filtro === 'entregados'
          ? p.estado === 'entregado'
          : p.estado !== 'entregado',
    )
    .sort((a, b) => ORDEN[a.estado] - ORDEN[b.estado] || a.numero.localeCompare(b.numero));

  return (
    <Pantalla refrescando={pedidos.isFetching} onRefrescar={() => pedidos.refetch()}>
      <View className="flex-row gap-2" accessibilityRole="tablist">
        {(
          [
            ['pendientes', 'Pendientes'],
            ['entregados', 'Entregados'],
            ['todos', 'Todos'],
          ] as const
        ).map(([valor, etiqueta]) => (
          <Pressable
            key={valor}
            accessibilityRole="tab"
            accessibilityState={{ selected: filtro === valor }}
            onPress={() => setFiltro(valor)}
            className={`h-12 items-center justify-center rounded-pill px-4 ${filtro === valor ? 'bg-charcoal' : 'bg-surface border border-border'}`}>
            <Texto variante="label-md" tono={filtro === valor ? 'claro' : 'normal'}>
              {etiqueta}
            </Texto>
          </Pressable>
        ))}
      </View>
      {pedidos.isError && !pedidos.data ? (
        <ErrorCarga error={pedidos.error} onReintentar={() => pedidos.refetch()} />
      ) : null}
      {pedidos.data && lista.length === 0 ? (
        <Vacio
          icono="inbox"
          titulo="Nada por acá"
          detalle={
            filtro === 'pendientes'
              ? 'No quedan entregas pendientes para hoy.'
              : 'Sin pedidos en este filtro.'
          }
        />
      ) : null}
      {lista.map((p) => (
        <TarjetaPedido
          key={p.id}
          pedido={p}
          onPress={() => router.push({ pathname: '/(reparto)/entrega/[id]', params: { id: p.id } })}
          accionPrincipal={
            p.estado === 'en_camino'
              ? {
                  texto: 'Registrar entrega',
                  icono: 'cash-register',
                  onPress: () =>
                    router.push({ pathname: '/(reparto)/entrega/[id]', params: { id: p.id } }),
                }
              : p.sin_pesar.length
                ? {
                    texto: 'Pesar',
                    icono: 'scale',
                    onPress: () =>
                      router.push({ pathname: '/(reparto)/pesada/[id]', params: { id: p.id } }),
                  }
                : undefined
          }
        />
      ))}
    </Pantalla>
  );
}

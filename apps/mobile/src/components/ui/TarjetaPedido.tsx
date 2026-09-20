import { Linking, Pressable, View } from 'react-native';

import { Boton, BotonIcono } from '@/components/ui/Boton';
import { Badge, Stepper } from '@/components/ui/Estado';
import { Tarjeta } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import type { Pedido } from '@/lib/api';
import { cajones, kilos, pesos } from '@/lib/formato';

export function kilosPesados(pedido: Pedido): string {
  // Suma en centésimas de gramo como enteros para no perder precisión.
  const total = pedido.items.reduce(
    (acc, i) => acc + Math.round(Number(i.kg_pesados ?? 0) * 1000),
    0,
  );
  return (total / 1000).toFixed(3);
}

export function resumenProductos(pedido: Pedido): string {
  return pedido.items
    .map(
      (i) =>
        `${i.cajas ? `${i.cajas}× ` : ''}${i.producto_nombre}${i.kg_pedidos ? ` ${kilos(i.kg_pedidos)}` : ''}`,
    )
    .join(' · ');
}

export function abrirNavegacion(pedido: Pedido): void {
  const destino = encodeURIComponent(pedido.cliente_direccion || pedido.cliente_nombre);
  Linking.openURL(`https://www.google.com/maps/dir/?api=1&destination=${destino}`);
}

export function llamar(telefono: string | null): void {
  if (telefono) Linking.openURL(`tel:+${telefono}`);
}

/**
 * Order card: cliente y estado arriba, cajones y kilos en negrita tabular al medio, llamar y
 * navegar abajo.
 */
export function TarjetaPedido({
  pedido,
  onPress,
  accionPrincipal,
}: {
  pedido: Pedido;
  onPress?: () => void;
  accionPrincipal?: {
    texto: string;
    onPress: () => void;
    icono?: 'cash-register' | 'scale' | 'truck-check';
  };
}) {
  const pesado = pedido.sin_pesar.length === 0;
  // La cabecera es el área táctil para abrir el pedido; los botones de abajo van aparte para no
  // anidar botones (inválido en HTML y confuso para el lector de pantalla).
  return (
    <Tarjeta>
      <Pressable
        accessibilityRole={onPress ? 'button' : undefined}
        accessibilityLabel={
          onPress ? `Abrir pedido ${pedido.numero} de ${pedido.cliente_nombre}` : undefined
        }
        onPress={onPress}
        disabled={!onPress}>
        <View className="flex-row items-start justify-between gap-2">
          <View className="flex-1">
            <View className="flex-row items-center gap-2">
              <Texto variante="label-caps" tono="suave">
                #{pedido.numero}
              </Texto>
              {pedido.a_cuenta ? <Badge estado="pendiente" texto="Cta. cte." /> : null}
            </View>
            <Texto variante="headline-md" numberOfLines={1}>
              {pedido.cliente_nombre}
            </Texto>
            {pedido.cliente_direccion ? (
              <Texto variante="body-md" tono="suave" numberOfLines={1}>
                {pedido.cliente_direccion}
              </Texto>
            ) : null}
          </View>
          <View className="items-end gap-1">
            <Badge estado={pedido.estado} />
            <Texto variante="label-caps" tono="suave">
              Total
            </Texto>
            <Texto variante="body-metric">{pesado ? pesos(pedido.total) : '— sin pesar'}</Texto>
          </View>
        </View>

        <View className="mt-3 rounded-input bg-background px-3 py-2">
          <Texto variante="body-metric">
            {cajones(pedido.cajones)} · {kilos(kilosPesados(pedido))}
          </Texto>
          <Texto variante="body-md" tono="suave" numberOfLines={2}>
            {resumenProductos(pedido)}
          </Texto>
        </View>

        <View className="mt-3">
          <Stepper estado={pedido.estado} pesado={pesado} />
        </View>
      </Pressable>

      <View className="mt-3 flex-row items-center gap-2">
        <BotonIcono
          icono="phone"
          etiqueta={`Llamar a ${pedido.cliente_nombre}`}
          onPress={() => llamar(pedido.cliente_telefono)}
          disabled={!pedido.cliente_telefono}
        />
        <View className="flex-1">
          {accionPrincipal ? (
            <Boton
              texto={accionPrincipal.texto}
              icono={accionPrincipal.icono}
              onPress={accionPrincipal.onPress}
            />
          ) : (
            <Boton
              texto="Cómo llegar (GPS)"
              variante="secundario"
              icono="navigation-variant"
              onPress={() => abrirNavegacion(pedido)}
            />
          )}
        </View>
      </View>
    </Tarjeta>
  );
}

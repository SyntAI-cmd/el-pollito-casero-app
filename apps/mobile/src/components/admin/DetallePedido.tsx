import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Image, Linking, Pressable, View } from 'react-native';

import { Mapa } from '@/components/Mapa';
import { Boton } from '@/components/ui/Boton';
import { Campo } from '@/components/ui/Campo';
import { Badge, Stepper } from '@/components/ui/Estado';
import { Tarjeta } from '@/components/ui/Tarjeta';
import { kilosPesados } from '@/components/ui/TarjetaPedido';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver, mensajeDeError, type EstadoPedido, type Pedido } from '@/lib/api';
import { usePedido } from '@/lib/consultas';
import { ETIQUETA_ESTADO, ETIQUETA_TURNO, cajones, horaCorta, kilos, pesos } from '@/lib/formato';
import { tokens } from '@/theme/tokens';

const SIGUIENTES: Record<EstadoPedido, EstadoPedido[]> = {
  recibido: ['preparando', 'en_camino', 'cancelado'],
  preparando: ['en_camino', 'cancelado'],
  en_camino: ['entregado', 'cancelado'],
  entregado: [],
  cancelado: [],
};

/** Ficha del pedido para la vista partida de administración: estado, precios, fotos y borrado. */
export function DetallePedido({ id, onCerrar }: { id: string; onCerrar?: () => void }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const pedido = usePedido(id);
  const [precios, setPrecios] = useState<Record<string, string>>({});
  const [guardarPropio, setGuardarPropio] = useState(false);
  const [motivo, setMotivo] = useState('');
  const [confirmarBorrado, setConfirmarBorrado] = useState(false);
  const comprobantes = useQuery({
    queryKey: ['comprobantes', id],
    queryFn: async () =>
      desenvolver(
        await api.GET('/pedidos/{pedido_id}/comprobantes', { params: { path: { pedido_id: id } } }),
      ),
  });

  const refrescar = (actualizado?: Pedido) => {
    if (actualizado) queryClient.setQueryData(['pedido', id], actualizado);
    queryClient.invalidateQueries({ queryKey: ['pedidos'] });
    queryClient.invalidateQueries({ queryKey: ['nota'] });
    queryClient.invalidateQueries({ queryKey: ['pedido', id] });
  };

  const cambiarEstado = useMutation({
    mutationFn: async (estado: EstadoPedido) =>
      desenvolver(
        await api.POST('/pedidos/{pedido_id}/estado', {
          params: { path: { pedido_id: id } },
          body: { estado, motivo: estado === 'cancelado' ? motivo : null },
        }),
      ),
    onSuccess: (p) => refrescar(p),
  });
  const cambiarPrecios = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.PUT('/pedidos/{pedido_id}/precios', {
          params: { path: { pedido_id: id } },
          body: {
            precios: Object.entries(precios)
              .filter(([, v]) => v.trim())
              .map(([producto_codigo, precio]) => ({
                producto_codigo,
                precio: precio.replace(',', '.'),
                guardar_precio_propio: guardarPropio,
              })),
          },
        }),
      ),
    onSuccess: (p) => {
      setPrecios({});
      refrescar(p);
    },
  });
  const eliminar = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.DELETE('/pedidos/{pedido_id}', { params: { path: { pedido_id: id } } }),
      ),
    onSuccess: () => {
      refrescar();
      onCerrar?.();
    },
  });

  const p = pedido.data;
  if (!p)
    return (
      <Tarjeta>
        {pedido.isError ? (
          <Texto tono="peligro">{mensajeDeError(pedido.error)}</Texto>
        ) : (
          <Texto tono="suave">Cargando…</Texto>
        )}
      </Tarjeta>
    );
  const abierto = p.estado !== 'entregado' && p.estado !== 'cancelado';
  const hayCambios = Object.values(precios).some((v) => v.trim());

  return (
    <View className="gap-3">
      <Tarjeta elevada>
        <View className="flex-row items-start justify-between">
          <View>
            <Texto variante="label-caps" tono="suave">
              Pedido #{p.numero} · {ETIQUETA_TURNO[p.turno]} · {p.fecha_reparto}
            </Texto>
            <Pressable
              accessibilityRole="link"
              onPress={() =>
                router.push({ pathname: '/(admin)/clientes/[id]', params: { id: p.cliente_id } })
              }>
              <Texto variante="headline-lg" tono="primario">
                {p.cliente_nombre}
              </Texto>
            </Pressable>
            <Texto variante="body-md" tono="suave">
              {p.cliente_direccion || 'Sin dirección'}
              {p.cliente_telefono ? ` · +${p.cliente_telefono}` : ''}
            </Texto>
          </View>
          <View className="items-end gap-1">
            <Badge estado={p.estado} />
            {p.a_cuenta ? <Badge estado="pendiente" texto="Cta. cte." /> : null}
            {p.pagado ? <Badge estado="cobrado" texto="Cobrado" /> : null}
          </View>
        </View>
        <View className="mt-3">
          <Stepper estado={p.estado} pesado={p.sin_pesar.length === 0} />
        </View>
        <Texto variante="body-md" tono="suave" className="mt-2">
          Cargado {horaCorta(p.creado_en)} · Pesado {horaCorta(p.pesado_en)} · Entregado{' '}
          {horaCorta(p.entregado_en)}
          {p.motivo_cancelacion ? ` · Cancelado: ${p.motivo_cancelacion}` : ''}
        </Texto>
        {p.observaciones ? (
          <Texto variante="body-md" className="mt-1">
            Obs.: {p.observaciones}
          </Texto>
        ) : null}
      </Tarjeta>

      {p.cliente_lat && p.cliente_lng ? (
        <Mapa
          puntos={[
            { lat: Number(p.cliente_lat), lng: Number(p.cliente_lng), titulo: p.cliente_nombre },
          ]}
          alto={200}
        />
      ) : null}

      <Tarjeta>
        <View className="flex-row items-center justify-between">
          <Texto variante="headline-md">Renglones</Texto>
          <Texto variante="body-metric">
            {cajones(p.cajones)} · {kilos(kilosPesados(p))}
          </Texto>
        </View>
        {p.items.map((i) => (
          <View
            key={i.producto_codigo}
            className="mt-2 flex-row items-center gap-2 border-t border-border pt-2">
            <View className="flex-1">
              <Texto variante="body-lg">{i.producto_nombre}</Texto>
              <Texto variante="body-md" tono="suave">
                {i.cajas ? `${i.cajas} cajas · ` : ''}
                {i.kg_pedidos ? `${kilos(i.kg_pedidos)} pedidos · ` : ''}
                {i.kg_pesados ? `${kilos(i.kg_pesados)} pesados` : 'sin pesar'} ·{' '}
                {i.cajones_cargados}/{i.cajones} cargados
              </Texto>
            </View>
            <View className="w-[130px]">
              {abierto ? (
                <Campo
                  etiqueta="$/kg"
                  metrica
                  value={precios[i.producto_codigo] ?? ''}
                  onChangeText={(v) => setPrecios((x) => ({ ...x, [i.producto_codigo]: v }))}
                  placeholder={i.precio ?? 'sin precio'}
                />
              ) : (
                <Texto variante="body-metric">
                  {i.precio ? `${pesos(i.precio)}/kg` : 'sin precio'}
                </Texto>
              )}
            </View>
            <View className="w-[110px] items-end">
              <Texto variante="body-metric">{pesos(i.importe)}</Texto>
            </View>
          </View>
        ))}
        <View className="mt-2 flex-row items-center justify-between border-t border-border pt-2">
          <Texto variante="headline-md">Total</Texto>
          <Texto variante="headline-md">
            {p.sin_pesar.length
              ? `${pesos(p.total)} (faltan ${p.sin_pesar.join(', ')})`
              : pesos(p.total)}
          </Texto>
        </View>
        {abierto ? (
          <View className="mt-3 gap-2">
            <Pressable
              accessibilityRole="checkbox"
              accessibilityState={{ checked: guardarPropio }}
              onPress={() => setGuardarPropio((v) => !v)}
              className="min-h-[48px] flex-row items-center gap-2">
              <MaterialCommunityIcons
                name={guardarPropio ? 'checkbox-marked' : 'checkbox-blank-outline'}
                size={24}
                color={tokens.colors.primary}
              />
              <Texto variante="body-md">Guardar como precio propio del cliente</Texto>
            </Pressable>
            <Boton
              texto="Aplicar precios"
              icono="tag-check"
              variante="secundario"
              onPress={() => cambiarPrecios.mutate()}
              disabled={!hayCambios}
              cargando={cambiarPrecios.isPending}
            />
            {cambiarPrecios.isError ? (
              <Texto variante="body-md" tono="peligro">
                {mensajeDeError(cambiarPrecios.error)}
              </Texto>
            ) : null}
          </View>
        ) : null}
      </Tarjeta>

      <Tarjeta>
        <Texto variante="headline-md">Comprobantes</Texto>
        {comprobantes.data && comprobantes.data.length === 0 ? (
          <Texto variante="body-md" tono="suave">
            Sin fotos todavía.
          </Texto>
        ) : null}
        <View className="mt-2 flex-row flex-wrap gap-2">
          {(comprobantes.data ?? []).map((c) => (
            <Pressable
              key={c.id}
              accessibilityRole="link"
              accessibilityLabel={`Ver ${c.tipo}`}
              onPress={() => Linking.openURL(c.url)}>
              <Image source={{ uri: c.url }} style={{ width: 96, height: 96, borderRadius: 12 }} />
              <Texto variante="label-caps" tono="suave">
                {c.tipo === 'remito_firmado' ? 'Remito' : 'Comprobante'} {horaCorta(c.creado_en)}
              </Texto>
            </Pressable>
          ))}
        </View>
      </Tarjeta>

      {SIGUIENTES[p.estado].length ? (
        <Tarjeta>
          <Texto variante="headline-md">Cambiar estado</Texto>
          <View className="mt-2 flex-row flex-wrap gap-2">
            {SIGUIENTES[p.estado]
              .filter((e) => e !== 'cancelado')
              .map((e) => (
                <Boton
                  key={e}
                  texto={ETIQUETA_ESTADO[e]}
                  variante="secundario"
                  compacto
                  onPress={() => cambiarEstado.mutate(e)}
                  cargando={cambiarEstado.isPending}
                />
              ))}
          </View>
          <View className="mt-3 gap-2">
            <Campo
              etiqueta="Motivo de cancelación"
              value={motivo}
              onChangeText={setMotivo}
              placeholder="Obligatorio para cancelar"
            />
            <Boton
              texto="Cancelar pedido"
              variante="peligro"
              icono="close-circle"
              onPress={() => cambiarEstado.mutate('cancelado')}
              disabled={motivo.trim().length < 3}
            />
          </View>
          {cambiarEstado.isError ? (
            <Texto variante="body-md" tono="peligro">
              {mensajeDeError(cambiarEstado.error)}
            </Texto>
          ) : null}
        </Tarjeta>
      ) : null}

      <Tarjeta>
        <Texto variante="headline-md">Borrar pedido</Texto>
        <Texto variante="body-md" tono="suave">
          Borra sus cajones, deja auditoría y, si estaba cobrado, devuelve lo cobrado como saldo a
          favor.
        </Texto>
        <View className="mt-2 flex-row gap-2">
          {confirmarBorrado ? (
            <>
              <View className="flex-1">
                <Boton
                  texto="No, dejarlo"
                  variante="ghost"
                  onPress={() => setConfirmarBorrado(false)}
                />
              </View>
              <View className="flex-1">
                <Boton
                  texto="Sí, borrar"
                  variante="peligro"
                  icono="delete"
                  onPress={() => eliminar.mutate()}
                  cargando={eliminar.isPending}
                />
              </View>
            </>
          ) : (
            <Boton
              texto="Borrar pedido"
              variante="ghost"
              icono="delete"
              onPress={() => setConfirmarBorrado(true)}
            />
          )}
        </View>
        {eliminar.isError ? (
          <Texto variante="body-md" tono="peligro">
            {mensajeDeError(eliminar.error)}
          </Texto>
        ) : null}
      </Tarjeta>
    </View>
  );
}

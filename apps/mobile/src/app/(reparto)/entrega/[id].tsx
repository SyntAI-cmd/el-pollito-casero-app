import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { Boton, BotonIcono } from '@/components/ui/Boton';
import { Campo } from '@/components/ui/Campo';
import { Badge, Stepper } from '@/components/ui/Estado';
import { ErrorCarga, Pantalla } from '@/components/ui/Pantalla';
import { MetricaHero, Tarjeta } from '@/components/ui/Tarjeta';
import { abrirNavegacion, kilosPesados, llamar } from '@/components/ui/TarjetaPedido';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver, mensajeDeError } from '@/lib/api';
import { claves, usePedido } from '@/lib/consultas';
import { subirComprobante, tomarFoto } from '@/lib/foto';
import { cajones, horaCorta, kilos, pesos } from '@/lib/formato';
import { tokens } from '@/theme/tokens';

export default function EntregaEnCurso() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const pedido = usePedido(id);
  const [devueltos, setDevueltos] = useState('');
  const comprobantes = useQuery({
    queryKey: ['comprobantes', id],
    enabled: !!id,
    queryFn: async () =>
      desenvolver(
        await api.GET('/pedidos/{pedido_id}/comprobantes', {
          params: { path: { pedido_id: id } },
        }),
      ),
  });
  const fotoRemito = useMutation({
    mutationFn: async () => {
      const foto = await tomarFoto();
      if (!foto) return null;
      return subirComprobante(foto, 'remito_firmado', id);
    },
    onSuccess: () => comprobantes.refetch(),
  });

  const marcarEntregado = useMutation({
    mutationFn: async () => {
      const cantidad = Number(devueltos || 0);
      if (cantidad > 0) {
        desenvolver(
          await api.POST('/clientes/{cliente_id}/envases', {
            params: { path: { cliente_id: pedido.data!.cliente_id } },
            body: {
              dejados: 0,
              devueltos: cantidad,
              pedido_id: id,
              nota: `Devueltos en la entrega #${pedido.data!.numero}`,
            },
          }),
        );
      }
      return desenvolver(
        await api.POST('/pedidos/{pedido_id}/estado', {
          params: { path: { pedido_id: id } },
          body: { estado: 'entregado' },
        }),
      );
    },
    onSuccess: (actualizado) => {
      queryClient.setQueryData(claves.pedido(id), actualizado);
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
      router.back();
    },
  });

  if (pedido.isError && !pedido.data) {
    return (
      <Pantalla sinNav>
        <ErrorCarga error={pedido.error} onReintentar={() => pedido.refetch()} />
      </Pantalla>
    );
  }
  const p = pedido.data;
  if (!p) return <Pantalla sinNav>{null}</Pantalla>;

  const pesado = p.sin_pesar.length === 0;

  return (
    <>
      <Stack.Screen options={{ title: `Pedido #${p.numero}` }} />
      <Pantalla sinNav refrescando={pedido.isFetching} onRefrescar={() => pedido.refetch()}>
        <View className="flex-row items-center justify-between">
          <View>
            <Texto variante="label-caps" tono="suave">
              Entrega
            </Texto>
            <Texto variante="headline-lg">#{p.numero}</Texto>
          </View>
          <Badge estado={p.estado} />
        </View>

        <Tarjeta elevada>
          <Texto variante="label-caps" tono="suave">
            Cliente
          </Texto>
          <Texto variante="headline-md">{p.cliente_nombre}</Texto>
          {p.cliente_direccion ? (
            <View className="mt-1 flex-row items-center gap-1">
              <MaterialCommunityIcons
                name="map-marker"
                size={16}
                color={tokens.colors['on-surface-v']}
              />
              <Texto variante="body-md" tono="suave" className="flex-1">
                {p.cliente_direccion}
              </Texto>
            </View>
          ) : null}
          <View className="mt-3 flex-row flex-wrap gap-2">
            <View className="rounded-pill bg-background px-3 py-1.5">
              <Texto variante="body-metric">{cajones(p.cajones)}</Texto>
            </View>
            <View className="rounded-pill bg-background px-3 py-1.5">
              <Texto variante="body-metric">{kilos(kilosPesados(p))}</Texto>
            </View>
            {p.a_cuenta ? (
              <View className="rounded-pill bg-background px-3 py-1.5">
                <Texto variante="body-metric">Cuenta corriente</Texto>
              </View>
            ) : null}
          </View>
          <View className="mt-3 gap-1">
            {p.items.map((i) => (
              <View key={i.producto_codigo} className="flex-row justify-between">
                <Texto variante="body-md">
                  {i.cajas ? `${i.cajas}× ` : ''}
                  {i.producto_nombre}
                </Texto>
                <Texto variante="body-metric">
                  {i.kg_pesados
                    ? kilos(i.kg_pesados)
                    : i.kg_pedidos
                      ? `${kilos(i.kg_pedidos)} ped.`
                      : '—'}
                  {i.precio ? ` · ${pesos(i.precio)}/kg` : ' · sin precio'}
                </Texto>
              </View>
            ))}
          </View>
          <View className="mt-3 flex-row gap-2">
            <BotonIcono
              icono="phone"
              etiqueta="Llamar"
              onPress={() => llamar(p.cliente_telefono)}
              disabled={!p.cliente_telefono}
            />
            <View className="flex-1">
              <Boton
                texto="Cómo llegar (GPS)"
                variante="secundario"
                icono="navigation-variant"
                onPress={() => abrirNavegacion(p)}
              />
            </View>
          </View>
        </Tarjeta>

        <MetricaHero
          etiqueta="Total a cobrar en destino"
          valor={pesado ? pesos(p.total) : 'Sin pesar'}
          detalle={
            p.pagado
              ? 'Ya cobrado'
              : p.a_cuenta
                ? 'Va a la cuenta corriente: cobro opcional'
                : 'Efectivo, transferencia o cheque'
          }
          chip={
            <Badge
              estado={p.pagado ? 'cobrado' : p.a_cuenta ? 'pendiente' : 'deuda'}
              texto={p.pagado ? 'Cobrado' : 'Cobro pendiente'}
            />
          }
        />

        <Tarjeta>
          <Stepper estado={p.estado} pesado={pesado} />
          <View className="mt-3 gap-1">
            <Texto variante="body-md" tono="suave">
              Cargado {horaCorta(p.creado_en)} · Pesado {horaCorta(p.pesado_en)} · Entregado{' '}
              {horaCorta(p.entregado_en)}
            </Texto>
          </View>
        </Tarjeta>

        {p.estado === 'en_camino' ? (
          <Tarjeta>
            <Campo
              etiqueta="Cajones que devuelve el cliente"
              metrica
              value={devueltos}
              onChangeText={(t) => setDevueltos(t.replace(/[^0-9]/g, ''))}
              placeholder="0"
              ayuda="Se descuentan de los envases adeudados."
            />
            <View className="mt-4 gap-2">
              <View className="flex-row items-center justify-between">
                <Texto variante="body-md" tono={comprobantes.data?.length ? 'exito' : 'peligro'}>
                  {comprobantes.data?.length
                    ? `${comprobantes.data.length} ${comprobantes.data.length === 1 ? 'foto' : 'fotos'} (comprobante o remito)`
                    : 'Sin fotos: sacá la del remito firmado o del comprobante'}
                </Texto>
              </View>
              <Boton
                texto="Foto del remito firmado"
                icono="camera"
                variante="ghost"
                onPress={() => fotoRemito.mutate()}
                cargando={fotoRemito.isPending}
              />
              {fotoRemito.isError ? (
                <Texto variante="body-md" tono="peligro">
                  {mensajeDeError(fotoRemito.error)}
                </Texto>
              ) : null}
              <Boton
                texto="Registrar cobro"
                icono="cash-register"
                variante="secundario"
                onPress={() =>
                  router.push({ pathname: '/(reparto)/cobro/[id]', params: { id: p.id } })
                }
              />
              <Boton
                texto="Marcar entregado"
                icono="check-circle"
                onPress={() => marcarEntregado.mutate()}
                cargando={marcarEntregado.isPending}
                disabled={!comprobantes.data?.length}
              />
              {marcarEntregado.isError ? (
                <Texto variante="body-md" tono="peligro">
                  {mensajeDeError(marcarEntregado.error)}
                </Texto>
              ) : null}
            </View>
          </Tarjeta>
        ) : p.sin_pesar.length ? (
          <Boton
            texto="Pesar este pedido"
            icono="scale"
            onPress={() =>
              router.push({ pathname: '/(reparto)/pesada/[id]', params: { id: p.id } })
            }
          />
        ) : null}
      </Pantalla>
    </>
  );
}

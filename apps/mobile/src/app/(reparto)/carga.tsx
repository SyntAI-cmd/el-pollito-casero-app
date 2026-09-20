import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { Boton } from '@/components/ui/Boton';
import { Campo } from '@/components/ui/Campo';
import { Badge } from '@/components/ui/Estado';
import { ErrorCarga, Pantalla, Vacio } from '@/components/ui/Pantalla';
import { Tarjeta } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver, mensajeDeError, type Pedido } from '@/lib/api';
import { usePedidosDelDia, useSalidas } from '@/lib/consultas';
import { cajones as fmtCajones, hoyIso, kilos } from '@/lib/formato';
import { operarCajonLocal } from '@/lib/pesadaLocal';
import { useSesion } from '@/stores/sesion';
import { tokens } from '@/theme/tokens';

function CargaDePedido({ pedido }: { pedido: Pedido }) {
  const queryClient = useQueryClient();
  const cajones = useQuery({
    queryKey: ['cajones', pedido.id],
    queryFn: async () =>
      desenvolver(
        await api.GET('/pedidos/{pedido_id}/cajones', {
          params: { path: { pedido_id: pedido.id } },
        }),
      ),
  });
  const vivos = (cajones.data ?? []).filter((c) => !c.anulado);
  const nombre = (codigo: string) =>
    pedido.items.find((i) => i.producto_codigo === codigo)?.producto_nombre ?? codigo;
  return (
    <Tarjeta>
      <View className="flex-row items-start justify-between">
        <View className="flex-1">
          <Texto variante="label-caps" tono="suave">
            #{pedido.numero}
          </Texto>
          <Texto variante="headline-md" numberOfLines={1}>
            {pedido.cliente_nombre}
          </Texto>
        </View>
        <Badge
          estado={
            pedido.cajones > 0 && pedido.cajones_cargados === pedido.cajones
              ? 'entregado'
              : pedido.sin_pesar.length
                ? 'pendiente'
                : 'preparando'
          }
          texto={
            pedido.sin_pesar.length
              ? 'Falta pesar'
              : `${pedido.cajones_cargados}/${pedido.cajones} cargados`
          }
        />
      </View>
      {cajones.data && vivos.length === 0 ? (
        <Texto variante="body-md" tono="suave" className="mt-2">
          Sin cajones pesados todavía.
        </Texto>
      ) : null}
      <View className="mt-3 flex-row flex-wrap gap-2">
        {vivos.map((c, i) => (
          <Pressable
            key={c.id}
            accessibilityRole="checkbox"
            accessibilityState={{ checked: c.cargado }}
            accessibilityLabel={`Cajón ${i + 1} ${nombre(c.producto_codigo)} ${kilos(c.neto)}`}
            onPress={() =>
              operarCajonLocal(queryClient, pedido, c.id, c.cargado ? 'descargar' : 'cargar')
            }
            className={`min-h-[48px] flex-row items-center gap-2 rounded-pill border px-3 ${c.cargado ? 'border-success bg-success' : 'border-border bg-surface-white'}`}>
            <MaterialCommunityIcons
              name={c.cargado ? 'check-circle' : 'checkbox-blank-circle-outline'}
              size={20}
              color={c.cargado ? '#FFFFFF' : tokens.colors.pending}
            />
            <Texto variante="label-md" tono={c.cargado ? 'claro' : 'normal'}>
              {i + 1} · {nombre(c.producto_codigo)} {kilos(c.neto)}
            </Texto>
          </Pressable>
        ))}
      </View>
    </Tarjeta>
  );
}

export default function CargaDelCamion() {
  const queryClient = useQueryClient();
  const usuario = useSesion((s) => s.usuario);
  const hoy = hoyIso();
  const pedidos = usePedidosDelDia(hoy);
  const salidas = useSalidas(hoy);
  const vehiculos = useQuery({
    queryKey: ['vehiculos'],
    queryFn: async () => desenvolver(await api.GET('/vehiculos')),
  });
  const [vehiculoId, setVehiculoId] = useState<string | null>(null);
  const [motivo, setMotivo] = useState('');

  const miSalida = (salidas.data ?? []).find(
    (s) => s.preventista_id === usuario?.id || s.segundo_preventista_id === usuario?.id,
  );
  const abiertos = (pedidos.data ?? []).filter(
    (p) => p.estado === 'recibido' || p.estado === 'preparando',
  );
  const faltantes = abiertos.filter((p) => p.sin_pesar.length || p.cajones_cargados < p.cajones);

  const armarSalida = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.PUT('/salidas', {
          body: { vehiculo_id: vehiculoId!, fecha: hoy, preventista_id: usuario!.id },
        }),
      ),
    onSuccess: () => salidas.refetch(),
  });

  const cerrar = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.POST('/salidas/{salida_id}/cerrar', {
          params: { path: { salida_id: miSalida!.id } },
          body: { motivo: motivo.trim() || null },
        }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
      salidas.refetch();
    },
  });

  return (
    <Pantalla
      refrescando={pedidos.isFetching}
      onRefrescar={() => {
        pedidos.refetch();
        salidas.refetch();
      }}>
      <Tarjeta elevada>
        <Texto variante="label-caps" tono="suave">
          Salida del día
        </Texto>
        {miSalida ? (
          <>
            <Texto variante="headline-md">
              {miSalida.vehiculo_nombre} {miSalida.vehiculo_patente}
            </Texto>
            <Texto variante="body-md" tono="suave">
              {miSalida.preventista_nombre}
              {miSalida.segundo_preventista_nombre
                ? ` y ${miSalida.segundo_preventista_nombre}`
                : ''}{' '}
              · {miSalida.pedidos} pedidos
            </Texto>
            {miSalida.cerrada_en ? (
              <View className="mt-3">
                <Badge
                  estado="en_camino"
                  texto={`Salió ${miSalida.hora_salida?.slice(0, 5) ?? ''}`}
                />
              </View>
            ) : (
              <View className="mt-3 gap-2">
                {faltantes.length > 0 ? (
                  <>
                    <Texto variante="body-md" tono="peligro">
                      Falta pesar o cargar en {faltantes.map((p) => `#${p.numero}`).join(', ')}.
                      Para salir igual, anotá el motivo.
                    </Texto>
                    <Campo
                      etiqueta="Motivo para salir con faltantes"
                      value={motivo}
                      onChangeText={setMotivo}
                      placeholder="Ej.: las alas van en el segundo viaje"
                    />
                  </>
                ) : null}
                <Boton
                  texto="Cerrar camión"
                  icono="truck-fast"
                  onPress={() => cerrar.mutate()}
                  disabled={
                    abiertos.length === 0 || (faltantes.length > 0 && motivo.trim().length < 3)
                  }
                  cargando={cerrar.isPending}
                />
                {cerrar.isError ? (
                  <Texto variante="body-md" tono="peligro">
                    {mensajeDeError(cerrar.error)}
                  </Texto>
                ) : null}
              </View>
            )}
          </>
        ) : (
          <View className="mt-2 gap-3">
            <Texto variante="body-md" tono="suave">
              Todavía no tenés vehículo asignado para hoy. Elegí en cuál salís.
            </Texto>
            <View className="flex-row flex-wrap gap-2" accessibilityRole="radiogroup">
              {(vehiculos.data ?? []).map((v) => (
                <Pressable
                  key={v.id}
                  accessibilityRole="radio"
                  accessibilityState={{ checked: vehiculoId === v.id }}
                  onPress={() => setVehiculoId(v.id)}
                  className={`min-h-[48px] justify-center rounded-pill border px-4 ${vehiculoId === v.id ? 'border-primary bg-primary' : 'border-border bg-surface'}`}>
                  <Texto variante="label-md" tono={vehiculoId === v.id ? 'claro' : 'normal'}>
                    {v.nombre} · {v.patente}
                  </Texto>
                </Pressable>
              ))}
            </View>
            <Boton
              texto="Armar mi salida"
              icono="truck"
              variante="secundario"
              onPress={() => armarSalida.mutate()}
              disabled={!vehiculoId}
              cargando={armarSalida.isPending}
            />
            {armarSalida.isError ? (
              <Texto variante="body-md" tono="peligro">
                {mensajeDeError(armarSalida.error)}
              </Texto>
            ) : null}
          </View>
        )}
      </Tarjeta>

      <View>
        <Texto variante="headline-lg">Cajones a subir</Texto>
        <Texto variante="body-md" tono="suave">
          {fmtCajones(abiertos.reduce((a, p) => a + p.cajones, 0))} pesados ·{' '}
          {abiertos.reduce((a, p) => a + p.cajones_cargados, 0)} cargados
        </Texto>
      </View>
      {pedidos.isError && !pedidos.data ? (
        <ErrorCarga error={pedidos.error} onReintentar={() => pedidos.refetch()} />
      ) : null}
      {pedidos.data && abiertos.length === 0 ? (
        <Vacio
          icono="truck"
          titulo="Nada para cargar"
          detalle="Los pedidos de hoy ya salieron o no hay pedidos cargados."
        />
      ) : null}
      {abiertos.map((p) => (
        <CargaDePedido key={p.id} pedido={p} />
      ))}
    </Pantalla>
  );
}

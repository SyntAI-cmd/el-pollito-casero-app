import { useQuery, useQueryClient } from '@tanstack/react-query';
import * as Haptics from 'expo-haptics';
import { Stack, useLocalSearchParams } from 'expo-router';
import { useRef, useState } from 'react';
import { Platform, Pressable, TextInput, View } from 'react-native';

import { Boton } from '@/components/ui/Boton';
import { Campo } from '@/components/ui/Campo';
import { Badge } from '@/components/ui/Estado';
import { ErrorCarga, Pantalla } from '@/components/ui/Pantalla';
import { Tarjeta } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver, type Cajon } from '@/lib/api';
import { usePedido, useTara } from '@/lib/consultas';
import { cajones as fmtCajones, kilos } from '@/lib/formato';
import { aGramos, deGramos, netoDe, operarCajonLocal, pesarLocal } from '@/lib/pesadaLocal';

type Modo = 'cajon' | 'lote';

export default function Pesada() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const queryClient = useQueryClient();
  const pedido = usePedido(id);
  const tara = useTara();
  const [producto, setProducto] = useState<string | null>(null);
  const [modo, setModo] = useState<Modo>('cajon');
  const [bruto, setBruto] = useState('');
  const [cajas, setCajas] = useState('');
  const [anulando, setAnulando] = useState<{ id: string; motivo: string } | null>(null);
  const [guardando, setGuardando] = useState(false);
  const brutoRef = useRef<TextInput>(null);

  const cajonesQuery = useQuery({
    queryKey: ['cajones', id],
    enabled: !!id,
    queryFn: async () =>
      desenvolver(
        await api.GET('/pedidos/{pedido_id}/cajones', { params: { path: { pedido_id: id } } }),
      ),
  });

  const p = pedido.data;
  // Sin elección explícita, se propone el primer renglón al que le faltan cajas o kilos.
  const productoPorDefecto =
    p?.items.find((i) => i.cajas && i.cajones < i.cajas)?.producto_codigo ??
    p?.items.find((i) => !i.kg_pesados)?.producto_codigo ??
    p?.items[0]?.producto_codigo ??
    null;
  const productoElegido = producto ?? productoPorDefecto;

  if (pedido.isError && !p) {
    return (
      <Pantalla sinNav>
        <ErrorCarga error={pedido.error} onReintentar={() => pedido.refetch()} />
      </Pantalla>
    );
  }
  if (!p) return <Pantalla sinNav>{null}</Pantalla>;

  const item = p.items.find((i) => i.producto_codigo === productoElegido);
  const nCajas = Number(cajas || 0);
  const netoGramos =
    modo === 'cajon' ? netoDe(bruto, tara) : aGramos(bruto) - aGramos(tara) * nCajas;
  const neto = Number.isNaN(netoGramos) ? null : netoGramos;
  const valido =
    !!item &&
    neto !== null &&
    neto > 0 &&
    (modo === 'cajon' || (nCajas >= 1 && nCajas <= 500)) &&
    (p.estado === 'recibido' || p.estado === 'preparando');
  const porCajon =
    modo === 'lote' && neto !== null && nCajas > 0 ? Math.floor(neto / nCajas) : null;

  const confirmar = async () => {
    if (!valido || !item || neto === null) return;
    setGuardando(true);
    try {
      await pesarLocal(
        queryClient,
        p,
        modo === 'cajon'
          ? {
              modo,
              producto_codigo: item.producto_codigo,
              bruto: deGramos(aGramos(bruto)),
              netoGramos: neto,
            }
          : {
              modo,
              producto_codigo: item.producto_codigo,
              cajas: nCajas,
              bruto_total: deGramos(aGramos(bruto)),
              netoGramos: neto,
            },
      );
      if (Platform.OS !== 'web')
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      setBruto('');
      setCajas('');
      brutoRef.current?.focus();
    } finally {
      setGuardando(false);
    }
  };

  const listaCajones: Cajon[] = (cajonesQuery.data ?? []).filter((c) => !c.anulado);

  return (
    <>
      <Stack.Screen options={{ title: `Pesar #${p.numero}` }} />
      <Pantalla
        sinNav
        refrescando={pedido.isFetching}
        onRefrescar={() => {
          pedido.refetch();
          cajonesQuery.refetch();
        }}>
        <View className="flex-row items-center justify-between">
          <View className="flex-1">
            <Texto variante="headline-lg" numberOfLines={1}>
              {p.cliente_nombre}
            </Texto>
            <Texto variante="body-md" tono="suave">
              Tara {kilos(tara)} por cajón · {fmtCajones(p.cajones)} pesados
            </Texto>
          </View>
          <Badge estado={p.estado} />
        </View>

        {p.estado !== 'recibido' && p.estado !== 'preparando' ? (
          <Tarjeta>
            <Texto variante="body-lg">Este pedido ya salió: no se pesa más.</Texto>
          </Tarjeta>
        ) : null}

        <View className="flex-row flex-wrap gap-2" accessibilityRole="radiogroup">
          {p.items.map((i) => {
            const activo = i.producto_codigo === productoElegido;
            const progreso = i.cajas
              ? `${i.cajones}/${i.cajas} cajas`
              : i.kg_pedidos
                ? `${kilos(i.kg_pesados ?? '0')} de ${kilos(i.kg_pedidos)}`
                : `${i.cajones} cajones`;
            return (
              <Pressable
                key={i.producto_codigo}
                accessibilityRole="radio"
                accessibilityState={{ checked: activo }}
                onPress={() => setProducto(i.producto_codigo)}
                className={`min-h-[48px] justify-center rounded-pill border px-4 py-2 ${activo ? 'border-primary bg-primary' : 'border-border bg-surface'}`}>
                <Texto variante="label-md" tono={activo ? 'claro' : 'normal'}>
                  {i.producto_nombre}
                </Texto>
                <Texto
                  variante="label-caps"
                  className={activo ? 'text-white/70' : 'text-on-surface-v'}>
                  {progreso}
                </Texto>
              </Pressable>
            );
          })}
        </View>

        <Tarjeta elevada>
          <View className="flex-row gap-2" accessibilityRole="tablist">
            {(
              [
                ['cajon', 'Cajón por cajón'],
                ['lote', 'Por lote'],
              ] as const
            ).map(([valor, etiqueta]) => (
              <Pressable
                key={valor}
                accessibilityRole="tab"
                accessibilityState={{ selected: modo === valor }}
                onPress={() => setModo(valor)}
                className={`h-12 flex-1 items-center justify-center rounded-pill ${modo === valor ? 'bg-charcoal' : 'border border-border bg-surface'}`}>
                <Texto variante="label-md" tono={modo === valor ? 'claro' : 'normal'}>
                  {etiqueta}
                </Texto>
              </Pressable>
            ))}
          </View>

          <View className="mt-4 gap-3">
            {modo === 'lote' ? (
              <Campo
                etiqueta="Cantidad de cajas"
                metrica
                value={cajas}
                onChangeText={(t) => setCajas(t.replace(/[^0-9]/g, ''))}
                placeholder="0"
                returnKeyType="next"
                onSubmitEditing={() => brutoRef.current?.focus()}
              />
            ) : null}
            <Campo
              ref={brutoRef}
              etiqueta={modo === 'lote' ? 'Bruto total (kg)' : 'Bruto del cajón (kg)'}
              metrica
              value={bruto}
              onChangeText={setBruto}
              placeholder="0,000"
              autoFocus={Platform.OS === 'web'}
              returnKeyType="done"
              onSubmitEditing={confirmar}
              error={
                bruto && neto !== null && neto <= 0
                  ? 'El bruto no supera la tara'
                  : bruto && neto === null
                    ? 'Escribí los kilos con hasta 3 decimales'
                    : null
              }
            />
          </View>

          <View
            className="mt-4 items-center rounded-panel bg-background py-4"
            accessibilityLiveRegion="polite">
            <Texto variante="label-caps" tono="suave">
              Neto {modo === 'lote' ? 'total' : ''}
            </Texto>
            <Texto variante="display" tono={valido ? 'exito' : 'suave'}>
              {neto !== null && neto > 0 ? kilos(deGramos(neto)) : '— kg'}
            </Texto>
            {porCajon !== null && porCajon > 0 ? (
              <Texto variante="body-md" tono="suave">
                ≈ {kilos(deGramos(porCajon))} por cajón · {nCajas} cajones
              </Texto>
            ) : null}
          </View>

          <View className="mt-4">
            <Boton
              texto={modo === 'lote' ? 'Confirmar lote' : 'Confirmar cajón'}
              icono="check"
              onPress={confirmar}
              disabled={!valido}
              cargando={guardando}
            />
          </View>
        </Tarjeta>

        <View>
          <Texto variante="headline-md">Cajones pesados</Texto>
          {cajonesQuery.data && listaCajones.length === 0 ? (
            <Texto variante="body-md" tono="suave">
              Todavía no hay cajones en el servidor.
            </Texto>
          ) : null}
        </View>
        {listaCajones.map((c, i) => (
          <Tarjeta key={c.id}>
            <View className="flex-row items-center justify-between">
              <View>
                <Texto variante="body-metric">
                  {i + 1}.{' '}
                  {p.items.find((x) => x.producto_codigo === c.producto_codigo)?.producto_nombre ??
                    c.producto_codigo}{' '}
                  · {kilos(c.neto)}
                </Texto>
                <Texto variante="body-md" tono="suave">
                  Bruto {kilos(c.bruto)} · tara {kilos(c.tara)}
                  {c.cargado ? ' · cargado' : ''}
                </Texto>
              </View>
              {anulando?.id === c.id ? null : (
                <Boton
                  texto="Anular"
                  variante="ghost"
                  compacto
                  onPress={() => setAnulando({ id: c.id, motivo: '' })}
                  disabled={c.cargado}
                />
              )}
            </View>
            {anulando?.id === c.id ? (
              <View className="mt-3 gap-2">
                <Campo
                  etiqueta="Motivo de la anulación"
                  value={anulando.motivo}
                  onChangeText={(motivo) => setAnulando({ id: c.id, motivo })}
                  placeholder="Caja rota, repetido…"
                />
                <View className="flex-row gap-2">
                  <View className="flex-1">
                    <Boton texto="Cancelar" variante="ghost" onPress={() => setAnulando(null)} />
                  </View>
                  <View className="flex-1">
                    <Boton
                      texto="Anular cajón"
                      variante="peligro"
                      disabled={anulando.motivo.trim().length < 3}
                      onPress={async () => {
                        await operarCajonLocal(
                          queryClient,
                          p,
                          c.id,
                          'anular',
                          anulando.motivo.trim(),
                        );
                        setAnulando(null);
                      }}
                    />
                  </View>
                </View>
              </View>
            ) : null}
          </Tarjeta>
        ))}
      </Pantalla>
    </>
  );
}

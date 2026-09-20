import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { View } from 'react-native';

import { Boton } from '@/components/ui/Boton';
import { Campo } from '@/components/ui/Campo';
import { Badge } from '@/components/ui/Estado';
import { ErrorCarga, Pantalla } from '@/components/ui/Pantalla';
import { MetricaHero, Tarjeta } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver, mensajeDeError } from '@/lib/api';
import { fechaLarga, horaCorta, hoyIso, pesos } from '@/lib/formato';

const normalizar = (texto: string) => texto.replace(/\./g, '').replace(',', '.');

/** Cierre de caja del día: efectivo que debía rendir vs. recibido. Transferencias y cheques aparte. */
export default function MiCaja() {
  const queryClient = useQueryClient();
  const hoy = hoyIso();
  const [recibido, setRecibido] = useState('');
  const [nota, setNota] = useState('');
  const caja = useQuery({
    queryKey: ['caja', hoy],
    queryFn: async () => desenvolver(await api.GET('/caja', { params: { query: { fecha: hoy } } })),
  });
  const cerrar = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.POST('/caja/cierres', {
          body: { fecha: hoy, efectivo_recibido: normalizar(recibido), nota },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['caja'] }),
  });

  const c = caja.data;
  // Centavos enteros para comparar sin errores de coma flotante.
  const diferencia =
    c && recibido
      ? Math.round(Number(normalizar(recibido)) * 100) -
        Math.round(Number(c.efectivo_esperado) * 100)
      : null;
  const cuadra = diferencia === 0;

  return (
    <Pantalla refrescando={caja.isFetching} onRefrescar={() => caja.refetch()}>
      {caja.isError && !c ? (
        <ErrorCarga error={caja.error} onReintentar={() => caja.refetch()} />
      ) : null}
      {c ? (
        <>
          <MetricaHero
            etiqueta="Efectivo a rendir"
            valor={pesos(c.efectivo_esperado)}
            detalle={`${c.cantidad_cobros} ${c.cantidad_cobros === 1 ? 'cobro' : 'cobros'} · ${fechaLarga(hoy)}`}
            chip={
              c.cierre ? (
                <Badge estado="cobrado" texto="Caja cerrada" />
              ) : (
                <Badge estado="pendiente" texto="Abierta" />
              )
            }
          />
          <Tarjeta>
            <Texto variante="label-caps" tono="suave">
              No suman al efectivo
            </Texto>
            <View className="mt-1 flex-row justify-between">
              <Texto variante="body-lg">Transferencias</Texto>
              <Texto variante="body-metric">{pesos(c.transferencias)}</Texto>
            </View>
            <View className="flex-row justify-between">
              <Texto variante="body-lg">Cheques</Texto>
              <Texto variante="body-metric">{pesos(c.cheques)}</Texto>
            </View>
            <View className="mt-2 flex-row justify-between border-t border-border pt-2">
              <Texto variante="body-lg">Total cobrado</Texto>
              <Texto variante="body-metric">{pesos(c.total_cobrado)}</Texto>
            </View>
          </Tarjeta>

          {c.cierre ? (
            <Tarjeta elevada>
              <Texto variante="headline-md">Cierre registrado</Texto>
              <Texto variante="body-md" tono="suave">
                Recibido {pesos(c.cierre.efectivo_recibido)} · diferencia{' '}
                {pesos(c.cierre.diferencia)} · {horaCorta(c.cierre.cerrado_en)}
              </Texto>
              {c.cierre.nota ? <Texto variante="body-md">{c.cierre.nota}</Texto> : null}
            </Tarjeta>
          ) : (
            <Tarjeta elevada>
              <Texto variante="headline-md">Rendir la caja</Texto>
              <View className="mt-3 gap-3">
                <Campo
                  etiqueta="Efectivo que entregás"
                  metrica
                  value={recibido}
                  onChangeText={setRecibido}
                  placeholder={c.efectivo_esperado}
                />
                {diferencia !== null ? (
                  <Texto variante="body-md" tono={cuadra ? 'exito' : 'peligro'}>
                    {cuadra
                      ? 'La caja cuadra.'
                      : `${diferencia < 0 ? 'Faltan' : 'Sobran'} ${pesos((Math.abs(diferencia) / 100).toFixed(2))}: anotá el motivo.`}
                  </Texto>
                ) : null}
                <Campo
                  etiqueta="Nota"
                  value={nota}
                  onChangeText={setNota}
                  placeholder={cuadra ? 'Opcional' : 'Obligatoria si no cuadra'}
                />
                <Boton
                  texto="Cerrar mi caja"
                  icono="lock-check"
                  onPress={() => cerrar.mutate()}
                  disabled={!recibido || (diferencia !== 0 && nota.trim().length < 3)}
                  cargando={cerrar.isPending}
                />
                {cerrar.isError ? (
                  <Texto variante="body-md" tono="peligro">
                    {mensajeDeError(cerrar.error)}
                  </Texto>
                ) : null}
              </View>
            </Tarjeta>
          )}

          <Texto variante="headline-md">Cobros del día</Texto>
          {c.pagos.length === 0 ? (
            <Texto variante="body-md" tono="suave">
              Todavía no registraste cobros hoy.
            </Texto>
          ) : null}
          {c.pagos.map((p) => (
            <Tarjeta key={p.id}>
              <View className="flex-row items-center justify-between">
                <View className="flex-1">
                  <Texto variante="headline-md" numberOfLines={1}>
                    {p.cliente_nombre}
                  </Texto>
                  <Texto variante="body-md" tono="suave">
                    {horaCorta(p.fecha)} ·{' '}
                    {p.partes.map((x) => `${x.medio} ${pesos(x.importe)}`).join(' + ')}
                    {p.pedidos_cubiertos.length
                      ? ` · cubre #${p.pedidos_cubiertos.join(', #')}`
                      : ''}
                  </Texto>
                </View>
                <Texto variante="body-metric">{pesos(p.total)}</Texto>
              </View>
            </Tarjeta>
          ))}
        </>
      ) : null}
    </Pantalla>
  );
}

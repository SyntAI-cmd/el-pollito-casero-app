import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Image, Linking, Pressable, View } from 'react-native';

import { Seccion, SelectorFecha, Tabla } from '@/components/admin/controles';
import { Boton } from '@/components/ui/Boton';
import { Campo } from '@/components/ui/Campo';
import { Badge } from '@/components/ui/Estado';
import { ErrorCarga, Pantalla, Vacio } from '@/components/ui/Pantalla';
import { Tarjeta } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver, mensajeDeError, type Esquemas } from '@/lib/api';
import { horaCorta, hoyIso, pesos } from '@/lib/formato';

type Resumen = Esquemas['ResumenCaja'];

function CajaDe({ resumen, fecha }: { resumen: Resumen; fecha: string }) {
  const queryClient = useQueryClient();
  const [recibido, setRecibido] = useState('');
  const [nota, setNota] = useState('');
  const cerrar = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.POST('/caja/cierres', {
          body: {
            usuario_id: resumen.usuario_id,
            fecha,
            efectivo_recibido: recibido.replace(/\./g, '').replace(',', '.'),
            nota,
          },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['rendicion'] }),
  });
  const diferencia = recibido
    ? Math.round(Number(recibido.replace(/\./g, '').replace(',', '.')) * 100) -
      Math.round(Number(resumen.efectivo_esperado) * 100)
    : null;
  return (
    <Tarjeta elevada>
      <View className="flex-row items-start justify-between">
        <View>
          <Texto variante="headline-md">{resumen.usuario_nombre}</Texto>
          <Texto variante="body-md" tono="suave">
            {resumen.cantidad_cobros} cobros · total {pesos(resumen.total_cobrado)}
          </Texto>
        </View>
        {resumen.cierre ? (
          <Badge
            estado={Number(resumen.cierre.diferencia) === 0 ? 'cobrado' : 'deuda'}
            texto={`Cerrada · dif. ${pesos(resumen.cierre.diferencia)}`}
          />
        ) : (
          <Badge estado="pendiente" texto="Sin cerrar" />
        )}
      </View>
      <View className="mt-3 flex-row flex-wrap gap-3">
        {[
          ['Efectivo a rendir', resumen.efectivo_esperado],
          ['Transferencias', resumen.transferencias],
          ['Cheques', resumen.cheques],
        ].map(([etiqueta, valor]) => (
          <View
            key={etiqueta}
            className="min-w-[140px] flex-1 rounded-input bg-background px-3 py-2">
            <Texto variante="label-caps" tono="suave">
              {etiqueta}
            </Texto>
            <Texto variante="headline-md">{pesos(valor)}</Texto>
          </View>
        ))}
      </View>
      <Tabla
        columnas={[
          {
            clave: 'hora',
            titulo: 'Hora',
            ancho: 70,
            render: (p) => <Texto variante="body-md">{horaCorta(p.fecha)}</Texto>,
          },
          {
            clave: 'cliente',
            titulo: 'Cliente',
            ancho: 180,
            render: (p) => (
              <Texto variante="body-lg" numberOfLines={1}>
                {p.cliente_nombre}
              </Texto>
            ),
          },
          {
            clave: 'partes',
            titulo: 'Medios',
            ancho: 240,
            render: (p) => (
              <Texto variante="body-md" numberOfLines={1}>
                {p.partes.map((x) => `${x.medio} ${pesos(x.importe)}`).join(' + ')}
              </Texto>
            ),
          },
          {
            clave: 'cubre',
            titulo: 'Cubre',
            ancho: 120,
            render: (p) => (
              <Texto variante="body-md">
                {p.pedidos_cubiertos.length ? `#${p.pedidos_cubiertos.join(' #')}` : 'a cuenta'}
              </Texto>
            ),
          },
          {
            clave: 'total',
            titulo: 'Total',
            ancho: 110,
            alinear: 'derecha',
            render: (p) => <Texto variante="body-metric">{pesos(p.total)}</Texto>,
          },
        ]}
        filas={resumen.pagos}
        claveDe={(p) => p.id}
      />
      {resumen.cierre ? (
        <Texto variante="body-md" tono="suave" className="mt-2">
          Recibido {pesos(resumen.cierre.efectivo_recibido)} ·{' '}
          {horaCorta(resumen.cierre.cerrado_en)}
          {resumen.cierre.nota ? ` · ${resumen.cierre.nota}` : ''}
        </Texto>
      ) : (
        <View className="mt-3 flex-row flex-wrap items-end gap-2">
          <View className="min-w-[160px] flex-1">
            <Campo
              etiqueta="Efectivo recibido"
              metrica
              value={recibido}
              onChangeText={setRecibido}
              placeholder={resumen.efectivo_esperado}
            />
          </View>
          <View className="min-w-[200px] flex-[2]">
            <Campo
              etiqueta="Nota"
              value={nota}
              onChangeText={setNota}
              placeholder={
                diferencia !== null && diferencia !== 0 ? 'Obligatoria: no cuadra' : 'Opcional'
              }
            />
          </View>
          <Boton
            texto="Cerrar caja"
            icono="lock-check"
            compacto
            onPress={() => cerrar.mutate()}
            disabled={!recibido || (diferencia !== 0 && nota.trim().length < 3)}
            cargando={cerrar.isPending}
          />
        </View>
      )}
      {cerrar.isError ? (
        <Texto variante="body-md" tono="peligro">
          {mensajeDeError(cerrar.error)}
        </Texto>
      ) : null}
    </Tarjeta>
  );
}

export default function Rendicion() {
  const [fecha, setFecha] = useState(hoyIso());
  const rendicion = useQuery({
    queryKey: ['rendicion', fecha],
    queryFn: async () =>
      desenvolver(await api.GET('/caja/rendicion', { params: { query: { fecha } } })),
  });
  const comprobantes = useQuery({
    queryKey: ['comprobantes-dia', fecha],
    queryFn: async () =>
      desenvolver(await api.GET('/comprobantes', { params: { query: { fecha } } })),
  });
  return (
    <Pantalla sinNav refrescando={rendicion.isFetching} onRefrescar={() => rendicion.refetch()}>
      <SelectorFecha valor={fecha} onCambio={setFecha} />
      {rendicion.isError && !rendicion.data ? (
        <ErrorCarga error={rendicion.error} onReintentar={() => rendicion.refetch()} />
      ) : null}
      {rendicion.data && rendicion.data.length === 0 ? (
        <Vacio
          icono="inbox"
          titulo="Nadie cobró este día"
          detalle="Las cajas aparecen cuando hay cobros registrados."
        />
      ) : null}
      {(rendicion.data ?? []).map((r) => (
        <CajaDe key={r.usuario_id} resumen={r} fecha={fecha} />
      ))}
      <Seccion
        titulo="Comprobantes del día"
        detalle="Fotos de transferencias, cheques y remitos firmados, para conciliar">
        {comprobantes.data && comprobantes.data.length === 0 ? (
          <Texto variante="body-md" tono="suave">
            Sin fotos este día.
          </Texto>
        ) : null}
        <View className="flex-row flex-wrap gap-2">
          {(comprobantes.data ?? []).map((c) => (
            <Pressable
              key={c.id}
              accessibilityRole="link"
              accessibilityLabel={`Ver ${c.tipo}`}
              onPress={() => Linking.openURL(c.url)}>
              <Image
                source={{ uri: c.url }}
                style={{ width: 110, height: 110, borderRadius: 12 }}
              />
              <Texto variante="label-caps" tono="suave">
                {c.tipo === 'remito_firmado' ? 'Remito' : 'Comprobante'} {horaCorta(c.creado_en)}
              </Texto>
            </Pressable>
          ))}
        </View>
      </Seccion>
    </Pantalla>
  );
}

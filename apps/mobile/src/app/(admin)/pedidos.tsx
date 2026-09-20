import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { ScrollView, View, useWindowDimensions } from 'react-native';

import { Chips, SelectorFecha, Tabla } from '@/components/admin/controles';
import { DetallePedido } from '@/components/admin/DetallePedido';
import { Boton } from '@/components/ui/Boton';
import { Badge } from '@/components/ui/Estado';
import { ErrorCarga, Pantalla, Vacio } from '@/components/ui/Pantalla';
import { TarjetaPedido } from '@/components/ui/TarjetaPedido';
import { Texto } from '@/components/ui/Texto';
import type { EstadoPedido, Pedido } from '@/lib/api';
import { usePedidosDelDia, useUsuarios } from '@/lib/consultas';
import { ETIQUETA_ESTADO, ETIQUETA_TURNO, hoyIso, kilos, pesos } from '@/lib/formato';

const ESTADOS: EstadoPedido[] = ['recibido', 'preparando', 'en_camino', 'entregado', 'cancelado'];

/**
 * Pedidos: lista densa con columnas fijas (o tarjetas) a la izquierda y ficha del pedido a la
 * derecha en escritorio (vista partida 7/5). En pantallas chicas, el detalle reemplaza la lista.
 */
export default function Pedidos() {
  const params = useLocalSearchParams<{ id?: string; fecha?: string }>();
  const router = useRouter();
  const { width } = useWindowDimensions();
  const escritorio = width >= 1024;
  const [fecha, setFecha] = useState(params.fecha ?? hoyIso());
  const [turno, setTurno] = useState<'manana' | 'tarde' | null>(null);
  const [estado, setEstado] = useState<EstadoPedido | null>(null);
  const [preventista, setPreventista] = useState<string | null>(null);
  const [vista, setVista] = useState<'tabla' | 'tarjetas'>('tabla');
  const [seleccionado, setSeleccionado] = useState<string | null>(params.id ?? null);
  const pedidos = usePedidosDelDia(fecha);
  const usuarios = useUsuarios();
  const nombres = new Map((usuarios.data ?? []).map((u) => [u.id, u.nombre]));

  const lista = (pedidos.data ?? [])
    .filter((p) => !turno || p.turno === turno)
    .filter((p) => !estado || p.estado === estado)
    .filter(
      (p) =>
        !preventista ||
        p.preventista_id === preventista ||
        p.segundo_preventista_id === preventista,
    )
    .sort((a, b) => a.numero.localeCompare(b.numero));

  const listado = (
    <View className="gap-3">
      <SelectorFecha valor={fecha} onCambio={setFecha} />
      <Chips
        opciones={[
          { valor: 'manana', etiqueta: 'Mañana' },
          { valor: 'tarde', etiqueta: 'Tarde' },
        ]}
        valor={turno}
        onCambio={setTurno}
      />
      <Chips
        opciones={ESTADOS.map((e) => ({ valor: e, etiqueta: ETIQUETA_ESTADO[e] }))}
        valor={estado}
        onCambio={setEstado}
      />
      <Chips
        opciones={(usuarios.data ?? [])
          .filter((u) => u.rol === 'preventista')
          .map((u) => ({ valor: u.id, etiqueta: u.nombre }))}
        valor={preventista}
        onCambio={setPreventista}
      />
      <View className="flex-row items-center justify-between">
        <Texto variante="body-md" tono="suave">
          {lista.length} pedidos ·{' '}
          {pesos(
            (lista.reduce((a, p) => a + Math.round(Number(p.total) * 100), 0) / 100).toFixed(2),
          )}
        </Texto>
        <View className="flex-row gap-2">
          <Boton
            texto="Tabla"
            variante={vista === 'tabla' ? 'secundario' : 'ghost'}
            compacto
            onPress={() => setVista('tabla')}
          />
          <Boton
            texto="Tarjetas"
            variante={vista === 'tarjetas' ? 'secundario' : 'ghost'}
            compacto
            onPress={() => setVista('tarjetas')}
          />
          <Boton
            texto="Nuevo"
            icono="plus"
            compacto
            onPress={() => router.push('/(admin)/nuevo-pedido')}
          />
        </View>
      </View>
      {pedidos.isError && !pedidos.data ? (
        <ErrorCarga error={pedidos.error} onReintentar={() => pedidos.refetch()} />
      ) : null}
      {pedidos.data && lista.length === 0 ? (
        <Vacio icono="inbox" titulo="Sin pedidos" detalle="Probá con otra fecha o quitá filtros." />
      ) : null}
      {vista === 'tabla' ? (
        <Tabla<Pedido>
          columnas={[
            {
              clave: 'numero',
              titulo: 'N°',
              ancho: 76,
              render: (p) => <Texto variante="body-metric">{p.numero}</Texto>,
            },
            {
              clave: 'cliente',
              titulo: 'Cliente',
              ancho: 200,
              render: (p) => (
                <Texto variante="body-lg" numberOfLines={1}>
                  {p.cliente_nombre}
                </Texto>
              ),
            },
            {
              clave: 'productos',
              titulo: 'Productos',
              ancho: 260,
              render: (p) => (
                <Texto variante="body-md" numberOfLines={1}>
                  {p.items
                    .map((i) => `${i.cajas ? `${i.cajas}× ` : ''}${i.producto_nombre}`)
                    .join(' · ')}
                </Texto>
              ),
            },
            {
              clave: 'kg',
              titulo: 'Kg',
              ancho: 90,
              alinear: 'derecha',
              render: (p) => (
                <Texto variante="body-metric">
                  {kilos(
                    (
                      p.items.reduce(
                        (a, i) => a + Math.round(Number(i.kg_pesados ?? 0) * 1000),
                        0,
                      ) / 1000
                    ).toFixed(3),
                  )}
                </Texto>
              ),
            },
            {
              clave: 'total',
              titulo: 'Importe',
              ancho: 110,
              alinear: 'derecha',
              render: (p) => (
                <Texto variante="body-metric">{p.sin_pesar.length ? '—' : pesos(p.total)}</Texto>
              ),
            },
            {
              clave: 'prev',
              titulo: 'Preventista',
              ancho: 130,
              render: (p) => (
                <Texto variante="body-md" numberOfLines={1}>
                  {p.preventista_id ? (nombres.get(p.preventista_id) ?? '…') : 'Sin asignar'}
                </Texto>
              ),
            },
            {
              clave: 'turno',
              titulo: 'Turno',
              ancho: 80,
              render: (p) => <Texto variante="body-md">{ETIQUETA_TURNO[p.turno]}</Texto>,
            },
            {
              clave: 'pago',
              titulo: 'Pago',
              ancho: 100,
              render: (p) => (
                <Badge
                  estado={p.pagado ? 'cobrado' : p.a_cuenta ? 'pendiente' : 'deuda'}
                  texto={p.pagado ? 'Cobrado' : p.a_cuenta ? 'Cta. cte.' : 'A cobrar'}
                />
              ),
            },
            {
              clave: 'cargado',
              titulo: 'Cargado',
              ancho: 90,
              alinear: 'derecha',
              render: (p) => (
                <Texto variante="body-metric">
                  {p.cajones_cargados}/{p.cajones}
                </Texto>
              ),
            },
            {
              clave: 'estado',
              titulo: 'Estado',
              ancho: 130,
              render: (p) => <Badge estado={p.estado} />,
            },
          ]}
          filas={lista}
          claveDe={(p) => p.id}
          onFila={(p) => setSeleccionado(p.id)}
          seleccionada={seleccionado}
        />
      ) : (
        lista.map((p) => (
          <TarjetaPedido key={p.id} pedido={p} onPress={() => setSeleccionado(p.id)} />
        ))
      )}
    </View>
  );

  if (escritorio) {
    return (
      <View className="flex-1 flex-row gap-6 p-gutter-desktop web:mx-auto web:w-full web:max-w-[1280px]">
        <ScrollView className="flex-[7]" contentContainerClassName="pb-8">
          {listado}
        </ScrollView>
        <ScrollView className="flex-[5]" contentContainerClassName="pb-8">
          {seleccionado ? (
            <DetallePedido id={seleccionado} onCerrar={() => setSeleccionado(null)} />
          ) : (
            <Vacio
              icono="inbox"
              titulo="Elegí un pedido"
              detalle="La ficha del pedido y del cliente aparece acá."
            />
          )}
        </ScrollView>
      </View>
    );
  }
  return (
    <Pantalla sinNav refrescando={pedidos.isFetching} onRefrescar={() => pedidos.refetch()}>
      {seleccionado ? (
        <>
          <Boton
            texto="Volver a la lista"
            variante="ghost"
            icono="arrow-left"
            onPress={() => setSeleccionado(null)}
          />
          <DetallePedido id={seleccionado} onCerrar={() => setSeleccionado(null)} />
        </>
      ) : (
        listado
      )}
    </Pantalla>
  );
}

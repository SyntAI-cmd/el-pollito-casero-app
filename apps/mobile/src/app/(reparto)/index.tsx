import { Stack, useRouter } from 'expo-router';
import { View } from 'react-native';

import { CerrarSesion } from '@/components/CerrarSesion';
import { Boton } from '@/components/ui/Boton';
import { Badge } from '@/components/ui/Estado';
import { ErrorCarga, Pantalla, Vacio } from '@/components/ui/Pantalla';
import { GrillaAccesos, MetricaHero, Tarjeta } from '@/components/ui/Tarjeta';
import { TarjetaPedido, kilosPesados } from '@/components/ui/TarjetaPedido';
import { Texto } from '@/components/ui/Texto';
import { usePedidosDelDia, useSalidas } from '@/lib/consultas';
import { cajones, fechaLarga, hoyIso, kilos } from '@/lib/formato';
import { useSesion } from '@/stores/sesion';

function sumarKilos(valores: string[]): string {
  const total = valores.reduce((acc, v) => acc + Math.round(Number(v) * 1000), 0);
  return (total / 1000).toFixed(3);
}

export default function InicioReparto() {
  const router = useRouter();
  const usuario = useSesion((s) => s.usuario);
  const hoy = hoyIso();
  const pedidos = usePedidosDelDia(hoy);
  const salidas = useSalidas(hoy);

  const lista = (pedidos.data ?? []).filter((p) => p.estado !== 'cancelado');
  const pendientes = lista.filter((p) => p.estado !== 'entregado');
  const enReparto = lista.filter((p) => p.estado === 'en_camino');
  const miSalida = (salidas.data ?? []).find(
    (s) => s.preventista_id === usuario?.id || s.segundo_preventista_id === usuario?.id,
  );

  return (
    <>
      <Stack.Screen options={{ headerRight: () => <CerrarSesion /> }} />
      <Pantalla
        refrescando={pedidos.isFetching || salidas.isFetching}
        onRefrescar={() => {
          pedidos.refetch();
          salidas.refetch();
        }}>
        <MetricaHero
          etiqueta={
            miSalida ? `Hoy sale ${miSalida.preventista_nombre}` : `Hola, ${usuario?.nombre ?? ''}`
          }
          valor={`${pendientes.length} ${pendientes.length === 1 ? 'parada' : 'paradas'} · ${kilos(sumarKilos(lista.map(kilosPesados)))}`}
          detalle={
            miSalida
              ? `${miSalida.vehiculo_nombre} ${miSalida.vehiculo_patente}${miSalida.hora_salida ? ` · sale ${miSalida.hora_salida.slice(0, 5)}` : ''}`
              : fechaLarga(hoy)
          }
          chip={
            miSalida ? (
              <Badge
                estado={miSalida.cerrada_en ? 'en_camino' : 'pendiente'}
                texto={miSalida.cerrada_en ? 'En ruta' : 'Sin salir'}
              />
            ) : null
          }>
        </MetricaHero>

        <GrillaAccesos
          accesos={[
            {
              icono: 'package-variant',
              subtitulo: 'Control',
              titulo: 'Mis entregas',
              contador: pendientes.length ? `${pendientes.length} pendientes` : undefined,
              onPress: () => router.push('/(reparto)/entregas'),
            },
            {
              icono: 'cart-plus',
              subtitulo: 'Venta rápida',
              titulo: 'Cargar pedido',
              onPress: () => router.push('/(reparto)/nuevo-pedido'),
            },
            {
              icono: 'scale',
              subtitulo: 'Kilos exactos',
              titulo: 'Balanza',
              contador: lista.some((p) => p.sin_pesar.length)
                ? `${lista.filter((p) => p.sin_pesar.length).length} sin pesar`
                : undefined,
              onPress: () => router.push('/(reparto)/pesada'),
            },
            {
              icono: 'truck-check',
              subtitulo: 'Cajones',
              titulo: 'Carga',
              contador: lista.length
                ? `${lista.reduce((a, p) => a + p.cajones - p.cajones_cargados, 0)} sin cargar`
                : undefined,
              onPress: () => router.push('/(reparto)/carga'),
            },
          ]}
        />

        <View className="flex-row items-end justify-between">
          <View>
            <Texto variante="headline-lg">Entregas prioritarias</Texto>
            <Texto variante="label-caps" tono="suave">
              En reparto primero
            </Texto>
          </View>
          {lista.length > 0 ? (
            <Boton
              texto={`Ver ${lista.length}`}
              variante="ghost"
              compacto
              onPress={() => router.push('/(reparto)/entregas')}
            />
          ) : null}
        </View>

        {pedidos.isError && !pedidos.data ? (
          <ErrorCarga error={pedidos.error} onReintentar={() => pedidos.refetch()} />
        ) : null}
        {pedidos.data && lista.length === 0 ? (
          <Vacio
            icono="truck"
            titulo="Sin pedidos para hoy"
            detalle="Cuando administración cargue la nota del día, aparecen acá."
          />
        ) : null}
        {[...enReparto, ...pendientes.filter((p) => p.estado !== 'en_camino')]
          .slice(0, 3)
          .map((p) => (
            <TarjetaPedido
              key={p.id}
              pedido={p}
              onPress={() =>
                router.push({ pathname: '/(reparto)/entrega/[id]', params: { id: p.id } })
              }
              accionPrincipal={
                p.estado === 'en_camino'
                  ? {
                      texto: 'Registrar entrega',
                      icono: 'cash-register',
                      onPress: () =>
                        router.push({ pathname: '/(reparto)/entrega/[id]', params: { id: p.id } }),
                    }
                  : undefined
              }
            />
          ))}

        {lista.length > 0 ? (
          <Tarjeta>
            <Texto variante="label-caps" tono="suave">
              Resumen del día
            </Texto>
            <Texto variante="body-metric" className="mt-1">
              {cajones(lista.reduce((a, p) => a + p.cajones, 0))} ·{' '}
              {lista.filter((p) => p.estado === 'entregado').length} de {lista.length} entregados
            </Texto>
          </Tarjeta>
        ) : null}
      </Pantalla>
    </>
  );
}

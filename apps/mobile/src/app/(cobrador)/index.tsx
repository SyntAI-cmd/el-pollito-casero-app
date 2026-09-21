import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { Stack, useRouter } from 'expo-router';
import { Linking, View } from 'react-native';

import { CerrarSesion } from '@/components/CerrarSesion';
import { Boton, BotonIcono } from '@/components/ui/Boton';
import { ErrorCarga, Pantalla, Vacio } from '@/components/ui/Pantalla';
import { MetricaHero, Tarjeta } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver } from '@/lib/api';
import { fechaLarga, horaCorta, hoyIso, pesos } from '@/lib/formato';
import { tokens } from '@/theme/tokens';

function sumar(valores: string[]): string {
  return (valores.reduce((a, v) => a + Math.round(Number(v) * 100), 0) / 100).toFixed(2);
}

/** Mis cuentas a cobrar: clientes con saldo, ordenados por zona (el servidor filtra por cobrador). */
export default function CuentasACobrar() {
  const router = useRouter();
  const cuentas = useQuery({
    queryKey: ['cuentas'],
    queryFn: async () => desenvolver(await api.GET('/cobranzas/cuentas')),
  });
  const lista = cuentas.data ?? [];

  return (
    <>
      <Stack.Screen options={{ headerRight: () => <CerrarSesion /> }} />
      <Pantalla refrescando={cuentas.isFetching} onRefrescar={() => cuentas.refetch()}>
        <MetricaHero
          etiqueta="A cobrar hoy"
          valor={pesos(sumar(lista.map((c) => c.saldo)))}
          detalle={`${lista.length} ${lista.length === 1 ? 'cuenta' : 'cuentas'} con saldo · ${fechaLarga(hoyIso())}`}
        />
        {cuentas.isError && !cuentas.data ? (
          <ErrorCarga error={cuentas.error} onReintentar={() => cuentas.refetch()} />
        ) : null}
        {cuentas.data && lista.length === 0 ? (
          <Vacio
            icono="inbox"
            titulo="Sin cuentas a cobrar"
            detalle="Ninguno de tus clientes asignados tiene saldo deudor."
          />
        ) : null}
        {lista.map((c) => (
          <Tarjeta key={c.cliente_id}>
            <View className="flex-row items-start justify-between gap-2">
              <View className="flex-1">
                <Texto variante="headline-md" numberOfLines={1}>
                  {c.nombre}
                </Texto>
                {c.direccion ? (
                  <View className="flex-row items-center gap-1">
                    <MaterialCommunityIcons
                      name="map-marker"
                      size={14}
                      color={tokens.colors['on-surface-v']}
                    />
                    <Texto variante="body-md" tono="suave" numberOfLines={1}>
                      {c.direccion}
                    </Texto>
                  </View>
                ) : null}
                <Texto variante="body-md" tono="suave">
                  {c.pedidos_pendientes} {c.pedidos_pendientes === 1 ? 'pedido' : 'pedidos'} sin
                  pagar
                  {c.ultimo_pago
                    ? ` · último pago ${new Date(c.ultimo_pago).toLocaleDateString('es-AR')} ${horaCorta(c.ultimo_pago)}`
                    : ' · sin pagos'}
                </Texto>
              </View>
              <View className="items-end">
                <Texto variante="label-caps" tono="peligro">
                  Saldo
                </Texto>
                <Texto variante="headline-md" tono="peligro">
                  {pesos(c.saldo)}
                </Texto>
              </View>
            </View>
            <View className="mt-3 flex-row items-center gap-2">
              <BotonIcono
                icono="phone"
                etiqueta={`Llamar a ${c.nombre}`}
                onPress={() => c.telefono && Linking.openURL(`tel:+${c.telefono}`)}
                disabled={!c.telefono}
              />
              <BotonIcono
                icono="navigation-variant"
                etiqueta="Cómo llegar"
                onPress={() =>
                  Linking.openURL(`geo:0,0?q=${encodeURIComponent(c.direccion || c.nombre)}`)
                }
                disabled={!c.direccion}
              />
              <View className="flex-1">
                <Boton
                  texto="Cobrar saldo"
                  icono="cash-register"
                  onPress={() =>
                    router.push({
                      pathname: '/(cobrador)/cobrar/[id]',
                      params: { id: c.cliente_id, nombre: c.nombre, saldo: c.saldo },
                    })
                  }
                />
              </View>
            </View>
          </Tarjeta>
        ))}
      </Pantalla>
    </>
  );
}

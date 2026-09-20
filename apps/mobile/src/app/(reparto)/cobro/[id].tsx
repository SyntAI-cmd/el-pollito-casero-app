import { useQuery } from '@tanstack/react-query';
import { Stack, useLocalSearchParams, useRouter } from 'expo-router';

import { Cobro } from '@/components/Cobro';
import { Badge } from '@/components/ui/Estado';
import { ErrorCarga, Pantalla } from '@/components/ui/Pantalla';
import { MetricaHero } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver } from '@/lib/api';
import { usePedido } from '@/lib/consultas';
import { pesos } from '@/lib/formato';

/** Centavos enteros para no perder precisión al descontar el saldo a favor. */
function menosSaldo(total: string, aFavor: string): { aCobrar: string; usado: string } {
  const t = Math.round(Number(total) * 100);
  const f = Math.round(Number(aFavor) * 100);
  const usado = Math.min(Math.max(f, 0), t);
  return { aCobrar: ((t - usado) / 100).toFixed(2), usado: (usado / 100).toFixed(2) };
}

export default function RegistrarCobro() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const pedido = usePedido(id);
  const extracto = useQuery({
    queryKey: ['extracto', pedido.data?.cliente_id],
    enabled: !!pedido.data,
    queryFn: async () =>
      desenvolver(
        await api.GET('/clientes/{cliente_id}/extracto', {
          params: { path: { cliente_id: pedido.data!.cliente_id } },
        }),
      ),
  });

  const p = pedido.data;
  if (pedido.isError && !p) {
    return (
      <Pantalla sinNav>
        <ErrorCarga error={pedido.error} onReintentar={() => pedido.refetch()} />
      </Pantalla>
    );
  }
  if (!p || (extracto.isPending && !extracto.data)) return <Pantalla sinNav>{null}</Pantalla>;

  const aFavor = extracto.data?.saldo_a_favor ?? '0';
  const { aCobrar, usado } = menosSaldo(p.total, aFavor);

  return (
    <>
      <Stack.Screen options={{ title: `Cobrar #${p.numero}` }} />
      <Pantalla sinNav>
        <MetricaHero
          etiqueta={p.cliente_nombre}
          valor={pesos(aCobrar)}
          detalle={
            Number(usado) > 0
              ? `Total ${pesos(p.total)} menos ${pesos(usado)} de saldo a favor`
              : `Total del pedido ${pesos(p.total)}`
          }
          chip={
            <Badge
              estado={p.pagado ? 'cobrado' : 'deuda'}
              texto={p.pagado ? 'Ya cobrado' : 'A cobrar'}
            />
          }
        />
        {p.pagado ? (
          <Texto variante="body-lg">Este pedido ya está cobrado.</Texto>
        ) : p.a_cuenta ? (
          <Texto variante="body-lg">
            Es un pedido a cuenta corriente: si el cliente paga, registrá un pago a cuenta desde su
            ficha (Cobranzas).
          </Texto>
        ) : Number(aCobrar) <= 0 ? (
          <Texto variante="body-lg">
            El saldo a favor cubre todo el pedido: no hay nada que cobrar.
          </Texto>
        ) : p.sin_pesar.length ? (
          <Texto variante="body-lg" tono="peligro">
            Falta pesar {p.sin_pesar.join(', ')}: el total todavía no es definitivo.
          </Texto>
        ) : (
          <Cobro
            clienteId={p.cliente_id}
            pedidoId={p.id}
            total={aCobrar}
            onListo={() => router.back()}
          />
        )}
      </Pantalla>
    </>
  );
}

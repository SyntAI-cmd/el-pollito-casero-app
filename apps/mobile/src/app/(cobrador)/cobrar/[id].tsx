import { Stack, useLocalSearchParams, useRouter } from 'expo-router';

import { Cobro } from '@/components/Cobro';
import { Pantalla } from '@/components/ui/Pantalla';
import { MetricaHero } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import { pesos } from '@/lib/formato';

/** Pago a cuenta: se aplica a los pedidos más viejos primero; el sobrante queda a favor. */
export default function CobrarCuenta() {
  const { id, nombre, saldo } = useLocalSearchParams<{
    id: string;
    nombre?: string;
    saldo?: string;
  }>();
  const router = useRouter();
  return (
    <>
      <Stack.Screen options={{ title: nombre ? `Cobrar a ${nombre}` : 'Cobrar' }} />
      <Pantalla sinNav>
        <MetricaHero
          etiqueta="Saldo de cuenta corriente"
          valor={saldo ? pesos(saldo) : '—'}
          detalle={nombre ?? ''}
        />
        <Texto variante="body-md" tono="suave">
          El importe puede ser parcial: se aplica a los pedidos más viejos primero y lo que sobra
          queda como saldo a favor.
        </Texto>
        <Cobro clienteId={id} pedidoId={null} total={null} onListo={() => router.back()} />
      </Pantalla>
    </>
  );
}

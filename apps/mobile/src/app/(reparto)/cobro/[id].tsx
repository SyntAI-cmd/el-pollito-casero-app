import { Stack, useLocalSearchParams } from 'expo-router';

import { Pantalla, Vacio } from '@/components/ui/Pantalla';

/** El cobro mixto con foto del comprobante llega con el módulo de cobros (Fase 5). */
export default function RegistrarCobro() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return (
    <>
      <Stack.Screen options={{ title: 'Registrar cobro' }} />
      <Pantalla sinNav>
        <Vacio
          icono="inbox"
          titulo="Cobro en construcción"
          detalle={`El cobro con efectivo, transferencia y cheque, y la foto del comprobante, llegan con la Fase 5. Pedido ${id}.`}
        />
      </Pantalla>
    </>
  );
}

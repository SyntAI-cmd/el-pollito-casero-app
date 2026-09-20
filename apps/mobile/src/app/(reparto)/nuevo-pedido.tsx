import { Stack, useRouter } from 'expo-router';

import { FormularioPedido } from '@/components/FormularioPedido';
import { Pantalla } from '@/components/ui/Pantalla';

export default function NuevoPedido() {
  const router = useRouter();
  return (
    <>
      <Stack.Screen options={{ title: 'Cargar pedido' }} />
      <Pantalla sinNav>
        <FormularioPedido
          onCreado={(pedido) =>
            router.replace({ pathname: '/(reparto)/entrega/[id]', params: { id: pedido.id } })
          }
        />
      </Pantalla>
    </>
  );
}

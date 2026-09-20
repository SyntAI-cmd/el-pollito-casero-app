import { useRouter } from 'expo-router';
import { useState } from 'react';

import { SelectorFecha } from '@/components/admin/controles';
import { FormularioPedido } from '@/components/FormularioPedido';
import { Pantalla } from '@/components/ui/Pantalla';
import { hoyIso } from '@/lib/formato';

export default function NuevoPedidoAdmin() {
  const router = useRouter();
  const [fecha, setFecha] = useState(hoyIso());
  return (
    <Pantalla sinNav>
      <SelectorFecha valor={fecha} onCambio={setFecha} />
      <FormularioPedido
        fecha={fecha}
        onCreado={(pedido) =>
          router.replace({ pathname: '/(admin)/pedidos', params: { id: pedido.id, fecha } })
        }
      />
    </Pantalla>
  );
}

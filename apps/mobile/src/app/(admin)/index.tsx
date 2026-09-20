import { Link, Stack } from 'expo-router';

import { CerrarSesion } from '@/components/CerrarSesion';
import { Boton } from '@/components/ui/Boton';
import { Pantalla, Vacio } from '@/components/ui/Pantalla';

/** La administración de escritorio (nota del día, pedidos, clientes, precios, rendición) llega con la Fase 6. */
export default function InicioAdmin() {
  return (
    <>
      <Stack.Screen options={{ title: 'Administración', headerRight: () => <CerrarSesion /> }} />
      <Pantalla sinNav>
        <Vacio
          icono="inbox"
          titulo="Administración en construcción"
          detalle="Mientras tanto, administración puede usar las pantallas de reparto para pesar, cargar y cargar pedidos."
        />
        <Link href="/(reparto)" asChild>
          <Boton
            texto="Ir a las pantallas de reparto"
            icono="truck-delivery"
            variante="secundario"
          />
        </Link>
      </Pantalla>
    </>
  );
}

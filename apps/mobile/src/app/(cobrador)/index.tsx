import { Stack } from 'expo-router';

import { Pantalla, Vacio } from '@/components/ui/Pantalla';
import { CerrarSesion } from '@/components/CerrarSesion';

/** Las pantallas del cobrador (cuentas a cobrar, cobro con foto, cierre de caja) llegan con la Fase 5. */
export default function InicioCobrador() {
  return (
    <>
      <Stack.Screen options={{ title: 'Cobranzas', headerRight: () => <CerrarSesion /> }} />
      <Pantalla sinNav>
        <Vacio
          icono="inbox"
          titulo="Cobranzas en construcción"
          detalle="Mis cuentas a cobrar, el cobro con foto y el cierre de caja llegan con la Fase 5."
        />
      </Pantalla>
    </>
  );
}

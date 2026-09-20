import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Pressable } from 'react-native';

import { useSesion } from '@/stores/sesion';

export function CerrarSesion() {
  const cerrar = useSesion((s) => s.cerrar);
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel="Cerrar sesión"
      onPress={() => cerrar()}
      className="h-12 w-12 items-center justify-center">
      <MaterialCommunityIcons name="logout" size={22} color="#FFFFFF" />
    </Pressable>
  );
}

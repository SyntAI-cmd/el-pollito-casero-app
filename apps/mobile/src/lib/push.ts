import { isRunningInExpoGo } from 'expo';
import * as Device from 'expo-device';
import { Platform } from 'react-native';

import { api } from '@/lib/api';

/**
 * Registra el token de push de Expo en el servidor. Solo en dispositivo físico: ni el
 * simulador ni el navegador reciben push. Un fallo acá nunca bloquea la app.
 *
 * `expo-notifications` se carga recién acá y nunca en Expo Go sobre Android: desde el SDK 53
 * el módulo tira un error al importarse en Expo Go (push remoto solo en builds propios), y un
 * import estático tumbaría el layout raíz entero.
 */
export async function registrarPush(): Promise<void> {
  if (Platform.OS === 'web' || !Device.isDevice) return;
  if (Platform.OS === 'android' && isRunningInExpoGo()) return;
  try {
    const Notifications = await import('expo-notifications');
    const permiso = await Notifications.getPermissionsAsync();
    const estado = permiso.granted ? permiso : await Notifications.requestPermissionsAsync();
    if (!estado.granted) return;
    if (Platform.OS === 'android') {
      await Notifications.setNotificationChannelAsync('reparto', {
        name: 'Reparto',
        importance: Notifications.AndroidImportance.HIGH,
      });
    }
    const { data: token } = await Notifications.getExpoPushTokenAsync();
    await api.POST('/auth/push-token', { body: { token, plataforma: Platform.OS } });
  } catch {
    /* sin proyecto EAS configurado o sin red: se reintenta en el próximo inicio */
  }
}

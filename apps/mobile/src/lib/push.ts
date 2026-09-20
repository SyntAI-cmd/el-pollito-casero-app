import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

import { api } from '@/lib/api';

/**
 * Registra el token de push de Expo en el servidor. Solo en dispositivo físico: ni el
 * simulador ni el navegador reciben push. Un fallo acá nunca bloquea la app.
 */
export async function registrarPush(): Promise<void> {
  if (Platform.OS === 'web' || !Device.isDevice) return;
  try {
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

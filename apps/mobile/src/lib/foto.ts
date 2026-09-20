import * as ImageManipulator from 'expo-image-manipulator';
import * as ImagePicker from 'expo-image-picker';

import { Platform } from 'react-native';

import { ApiError, apiBaseUrl, type Esquemas } from '@/lib/api';
import { useSesion } from '@/stores/sesion';

const MAXIMO_BYTES = 3.5 * 1024 * 1024;

export interface Foto {
  uri: string;
  bytes: number;
  ancho: number;
  alto: number;
}

/**
 * Saca una foto (o elige una) y la reduce en el celular antes de subir: JPEG de hasta ~3,5 MB
 * y 1600 px de lado mayor. Devuelve null si el usuario canceló.
 */
export async function tomarFoto(deGaleria = false): Promise<Foto | null> {
  const permiso = deGaleria
    ? await ImagePicker.requestMediaLibraryPermissionsAsync()
    : await ImagePicker.requestCameraPermissionsAsync();
  if (!permiso.granted) throw new Error('Sin permiso para usar la cámara');
  const resultado = deGaleria
    ? await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 1 })
    : await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 1 });
  if (resultado.canceled || !resultado.assets[0]) return null;
  return reducir(resultado.assets[0].uri, resultado.assets[0].width, resultado.assets[0].height);
}

async function reducir(uri: string, ancho: number, alto: number): Promise<Foto> {
  const contexto = ImageManipulator.ImageManipulator.manipulate(uri);
  const ladoMayor = Math.max(ancho, alto);
  if (ladoMayor > 1600) {
    const factor = 1600 / ladoMayor;
    contexto.resize({ width: Math.round(ancho * factor), height: Math.round(alto * factor) });
  }
  let calidad = 0.85;
  for (;;) {
    const imagen = await contexto.renderAsync();
    const salida = await imagen.saveAsync({
      format: ImageManipulator.SaveFormat.JPEG,
      compress: calidad,
    });
    const bytes = await tamano(salida.uri);
    if (bytes <= MAXIMO_BYTES || calidad <= 0.4) {
      return { uri: salida.uri, bytes, ancho: salida.width, alto: salida.height };
    }
    calidad -= 0.15;
  }
}

async function tamano(uri: string): Promise<number> {
  try {
    const respuesta = await fetch(uri);
    return (await respuesta.blob()).size;
  } catch {
    return 0;
  }
}

export type Comprobante = Esquemas['ComprobanteSalida'];

/** Sube la foto como multipart. En web la URI es un blob local; en el celular, un archivo. */
export async function subirComprobante(
  foto: Foto,
  tipo: 'comprobante' | 'remito_firmado',
  pedidoId: string | null,
): Promise<Comprobante> {
  const datos = new FormData();
  datos.append('tipo', tipo);
  if (pedidoId) datos.append('pedido_id', pedidoId);
  if (Platform.OS === 'web') {
    const blob = await (await fetch(foto.uri)).blob();
    datos.append('archivo', blob, 'foto.jpg');
  } else {
    datos.append('archivo', {
      uri: foto.uri,
      name: 'foto.jpg',
      type: 'image/jpeg',
    } as unknown as Blob);
  }
  const respuesta = await fetch(`${apiBaseUrl()}/comprobantes`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${useSesion.getState().acceso ?? ''}` },
    body: datos,
  });
  if (!respuesta.ok) {
    let mensaje = `Error ${respuesta.status}`;
    try {
      mensaje = ((await respuesta.json()) as { mensaje?: string }).mensaje ?? mensaje;
    } catch {
      /* sin cuerpo */
    }
    throw new ApiError(respuesta.status, mensaje);
  }
  return (await respuesta.json()) as Comprobante;
}

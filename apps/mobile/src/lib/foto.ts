import * as ImageManipulator from 'expo-image-manipulator';
import * as ImagePicker from 'expo-image-picker';

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

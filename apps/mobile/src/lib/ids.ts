import * as Crypto from 'expo-crypto';

/** Ids generadas en el celular: el servidor ignora duplicados por esta id (reintentos offline). */
export const nuevaId = (): string => Crypto.randomUUID();

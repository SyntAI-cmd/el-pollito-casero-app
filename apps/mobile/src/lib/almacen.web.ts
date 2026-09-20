/** Versión web del almacén local: localStorage. Misma interfaz que almacen.ts (SQLite). */
const PREFIJO = 'pollito.kv.';

function almacen(): Storage | null {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

export async function leer<T>(clave: string): Promise<T | null> {
  const crudo = almacen()?.getItem(PREFIJO + clave);
  return crudo ? (JSON.parse(crudo) as T) : null;
}

export async function guardar(clave: string, valor: unknown): Promise<void> {
  try {
    almacen()?.setItem(PREFIJO + clave, JSON.stringify(valor));
  } catch {
    /* sin espacio o modo privado: la pantalla sigue funcionando en memoria */
  }
}

export async function borrar(clave: string): Promise<void> {
  almacen()?.removeItem(PREFIJO + clave);
}

export async function vaciar(): Promise<void> {
  const s = almacen();
  if (!s) return;
  Object.keys(s)
    .filter((k) => k.startsWith(PREFIJO))
    .forEach((k) => s.removeItem(k));
}

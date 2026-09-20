import * as SQLite from 'expo-sqlite';

/**
 * Clave-valor sobre SQLite local (expo-sqlite). Es la fuente de verdad de la pantalla cuando
 * no hay señal: pedidos del día, cola de mutaciones, catálogo. En web hay otra implementación
 * (almacen.web.ts) sobre localStorage.
 */
let baseDatos: SQLite.SQLiteDatabase | null = null;

async function db(): Promise<SQLite.SQLiteDatabase> {
  if (!baseDatos) {
    baseDatos = await SQLite.openDatabaseAsync('pollito.db');
    await baseDatos.execAsync(
      'CREATE TABLE IF NOT EXISTS kv (clave TEXT PRIMARY KEY NOT NULL, valor TEXT NOT NULL, actualizado INTEGER NOT NULL)',
    );
  }
  return baseDatos;
}

export async function leer<T>(clave: string): Promise<T | null> {
  const fila = await (
    await db()
  ).getFirstAsync<{ valor: string }>('SELECT valor FROM kv WHERE clave = ?', clave);
  return fila ? (JSON.parse(fila.valor) as T) : null;
}

export async function guardar(clave: string, valor: unknown): Promise<void> {
  await (
    await db()
  ).runAsync(
    'INSERT OR REPLACE INTO kv (clave, valor, actualizado) VALUES (?, ?, ?)',
    clave,
    JSON.stringify(valor),
    Date.now(),
  );
}

export async function borrar(clave: string): Promise<void> {
  await (await db()).runAsync('DELETE FROM kv WHERE clave = ?', clave);
}

export async function vaciar(): Promise<void> {
  await (await db()).runAsync('DELETE FROM kv');
}

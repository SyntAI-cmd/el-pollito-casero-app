import type { QueryClient } from '@tanstack/react-query';

import * as almacen from '@/lib/almacen';
import type { Pedido } from '@/lib/api';
import { useCola } from '@/lib/cola';
import { claves } from '@/lib/consultas';
import { nuevaId } from '@/lib/ids';

/** Aritmética en gramos enteros: nada de floats con kilos. */
export function aGramos(texto: string): number {
  const limpio = texto.replace(',', '.').trim();
  if (!/^\d+(\.\d{0,3})?$/.test(limpio)) return NaN;
  const [entero, decimales = ''] = limpio.split('.');
  return Number(entero) * 1000 + Number(decimales.padEnd(3, '0'));
}

export const deGramos = (gramos: number): string => (gramos / 1000).toFixed(3);

export function netoDe(brutoTexto: string, taraTexto: string): number {
  const bruto = aGramos(brutoTexto);
  const tara = aGramos(taraTexto);
  if (Number.isNaN(bruto) || Number.isNaN(tara)) return NaN;
  return bruto - tara;
}

/**
 * Pesada escrita local primero: se actualiza la copia del pedido en pantalla y en SQLite, se
 * encola la mutación con id propia y se intenta mandar. Si no hay señal, queda en la cola.
 */
export async function pesarLocal(
  queryClient: QueryClient,
  pedido: Pedido,
  entrada:
    | { modo: 'cajon'; producto_codigo: string; bruto: string; netoGramos: number }
    | {
        modo: 'lote';
        producto_codigo: string;
        cajas: number;
        bruto_total: string;
        netoGramos: number;
      },
): Promise<void> {
  const cantidad = entrada.modo === 'lote' ? entrada.cajas : 1;
  const actualizado: Pedido = {
    ...pedido,
    estado: pedido.estado === 'recibido' ? 'preparando' : pedido.estado,
    cajones: pedido.cajones + cantidad,
    items: pedido.items.map((i) =>
      i.producto_codigo === entrada.producto_codigo
        ? {
            ...i,
            cajones: i.cajones + cantidad,
            kg_pesados: deGramos(Math.round(Number(i.kg_pesados ?? 0) * 1000) + entrada.netoGramos),
          }
        : i,
    ),
  };
  queryClient.setQueryData(claves.pedido(pedido.id), actualizado);
  await almacen.guardar(`pedido.${pedido.id}`, actualizado);

  const id = nuevaId();
  const ruta = `/pedidos/${pedido.id}/cajones${entrada.modo === 'lote' ? '/lote' : ''}`;
  const cuerpo =
    entrada.modo === 'lote'
      ? {
          lote_id: id,
          producto_codigo: entrada.producto_codigo,
          cajas: entrada.cajas,
          bruto_total: entrada.bruto_total,
          pesado_en: new Date().toISOString(),
        }
      : {
          id,
          producto_codigo: entrada.producto_codigo,
          bruto: entrada.bruto,
          pesado_en: new Date().toISOString(),
        };
  await useCola.getState().encolar({
    id,
    descripcion:
      entrada.modo === 'lote'
        ? `Lote ${entrada.cajas} cajas ${entrada.producto_codigo} · #${pedido.numero}`
        : `Cajón ${entrada.bruto} kg ${entrada.producto_codigo} · #${pedido.numero}`,
    metodo: 'POST',
    ruta,
    cuerpo,
    claveQuery: claves.pedido(pedido.id),
  });
  await useCola.getState().procesar((m) => {
    if (m.claveQuery) queryClient.invalidateQueries({ queryKey: m.claveQuery });
    queryClient.invalidateQueries({ queryKey: ['pedidos'] });
    queryClient.invalidateQueries({ queryKey: ['cajones', pedido.id] });
  });
}

export async function operarCajonLocal(
  queryClient: QueryClient,
  pedido: Pedido,
  cajonId: string,
  accion: 'cargar' | 'descargar' | 'anular',
  motivo?: string,
): Promise<void> {
  await useCola.getState().encolar({
    id: nuevaId(),
    descripcion: `${accion} cajón · #${pedido.numero}`,
    metodo: 'POST',
    ruta: `/cajones/${cajonId}/${accion}`,
    cuerpo: accion === 'anular' ? { motivo } : undefined,
    claveQuery: claves.pedido(pedido.id),
  });
  await useCola.getState().procesar((m) => {
    if (m.claveQuery) queryClient.invalidateQueries({ queryKey: m.claveQuery });
    queryClient.invalidateQueries({ queryKey: ['pedidos'] });
    queryClient.invalidateQueries({ queryKey: ['cajones'] });
  });
}

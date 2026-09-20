import { useQuery, useQueryClient, type QueryKey } from '@tanstack/react-query';
import { useEffect } from 'react';

import * as almacen from '@/lib/almacen';
import {
  api,
  desenvolver,
  wsUrl,
  type Cliente,
  type NotaDelDia,
  type Pedido,
  type PrecioResuelto,
  type Producto,
  type Salida,
  type Esquemas,
} from '@/lib/api';
import { useSesion } from '@/stores/sesion';

/**
 * Consulta con copia local: si la red falla y hay copia, se muestra la copia. Lo que llega
 * del servidor pisa la copia. Así la pantalla del repartidor sigue viva sin señal.
 */
async function conCopiaLocal<T>(clave: string, pedir: () => Promise<T>): Promise<T> {
  try {
    const datos = await pedir();
    await almacen.guardar(clave, datos);
    return datos;
  } catch (error) {
    const copia = await almacen.leer<T>(clave);
    if (copia !== null && error instanceof TypeError) return copia;
    throw error;
  }
}

export const claves = {
  pedidos: (fecha: string) => ['pedidos', fecha] as const,
  pedido: (id: string) => ['pedido', id] as const,
  productos: ['productos'] as const,
  salidas: (fecha: string) => ['salidas', fecha] as const,
  clientes: (q: string) => ['clientes', q] as const,
  preciosCliente: (id: string) => ['cliente', id, 'precios'] as const,
  sucursales: ['sucursales'] as const,
  nota: (fecha: string) => ['nota', fecha] as const,
};

export function usePedidosDelDia(fecha: string) {
  return useQuery({
    queryKey: claves.pedidos(fecha),
    queryFn: () =>
      conCopiaLocal<Pedido[]>(`pedidos.${fecha}`, async () =>
        desenvolver(await api.GET('/pedidos', { params: { query: { fecha, limite: 500 } } })),
      ),
  });
}

export function usePedido(id: string | undefined) {
  return useQuery({
    queryKey: claves.pedido(id ?? ''),
    enabled: !!id,
    queryFn: () =>
      conCopiaLocal<Pedido>(`pedido.${id}`, async () =>
        desenvolver(
          await api.GET('/pedidos/{pedido_id}', { params: { path: { pedido_id: id! } } }),
        ),
      ),
  });
}

export function useProductos() {
  return useQuery({
    queryKey: claves.productos,
    staleTime: 60 * 60 * 1000,
    queryFn: () =>
      conCopiaLocal<Producto[]>('productos', async () => desenvolver(await api.GET('/productos'))),
  });
}

export function useSalidas(fecha: string) {
  return useQuery({
    queryKey: claves.salidas(fecha),
    queryFn: () =>
      conCopiaLocal<Salida[]>(`salidas.${fecha}`, async () =>
        desenvolver(await api.GET('/salidas', { params: { query: { fecha } } })),
      ),
  });
}

export function useClientes(q: string) {
  return useQuery({
    queryKey: claves.clientes(q),
    queryFn: () =>
      conCopiaLocal<Cliente[]>(`clientes.${q}`, async () =>
        desenvolver(await api.GET('/clientes', { params: { query: { q: q || undefined } } })),
      ),
  });
}

export function usePreciosCliente(id: string | null) {
  return useQuery({
    queryKey: claves.preciosCliente(id ?? ''),
    enabled: !!id,
    queryFn: () =>
      conCopiaLocal<PrecioResuelto[]>(`precios.${id}`, async () =>
        desenvolver(
          await api.GET('/clientes/{cliente_id}/precios', {
            params: { path: { cliente_id: id! } },
          }),
        ),
      ),
  });
}

export function useSucursales() {
  return useQuery({
    queryKey: claves.sucursales,
    staleTime: 60 * 60 * 1000,
    queryFn: () =>
      conCopiaLocal<Esquemas['SucursalSalida'][]>('sucursales', async () =>
        desenvolver(await api.GET('/sucursales')),
      ),
  });
}

export function useUsuarios(habilitado = true) {
  return useQuery({
    queryKey: ['usuarios'],
    enabled: habilitado,
    staleTime: 5 * 60 * 1000,
    queryFn: () =>
      conCopiaLocal<Esquemas['UsuarioSalida'][]>('usuarios', async () =>
        desenvolver(await api.GET('/usuarios')),
      ),
  });
}

export function useNotaDelDia(fecha: string) {
  return useQuery({
    queryKey: claves.nota(fecha),
    queryFn: () =>
      conCopiaLocal<NotaDelDia>(`nota.${fecha}`, async () =>
        desenvolver(await api.GET('/pedidos/dia', { params: { query: { fecha } } })),
      ),
  });
}

/** Tara de la sucursal del usuario (para mostrar el neto al instante, antes de mandar). */
export function useTara(): string {
  const { data } = useSucursales();
  const sucursalId = useSesion((s) => s.usuario?.sucursal_id);
  return data?.find((s) => s.id === sucursalId)?.tara ?? '1.700';
}

interface EventoWs {
  tipo: string;
  datos: Record<string, unknown>;
}

/** Suscripción al canal de la sucursal: ante un evento, se invalida lo que corresponde. */
export function useTiempoReal(alEvento?: (evento: EventoWs) => void) {
  const token = useSesion((s) => s.acceso);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!token) return;
    let socket: WebSocket | null = null;
    let cerrado = false;
    let reintento: ReturnType<typeof setTimeout> | null = null;

    const conectar = () => {
      socket = new WebSocket(wsUrl(token));
      socket.onmessage = (mensaje) => {
        const evento = JSON.parse(String(mensaje.data)) as EventoWs;
        const invalidar: QueryKey[] = [];
        if (evento.tipo.startsWith('pedido.')) {
          invalidar.push(['pedidos'], ['nota'], ['salidas']);
          const pedidoId = evento.datos.pedido_id;
          if (typeof pedidoId === 'string') invalidar.push(claves.pedido(pedidoId));
        }
        if (evento.tipo.startsWith('flota.') || evento.tipo.startsWith('salida.')) {
          invalidar.push(['salidas']);
        }
        invalidar.forEach((clave) => queryClient.invalidateQueries({ queryKey: clave }));
        alEvento?.(evento);
      };
      socket.onclose = () => {
        if (!cerrado) reintento = setTimeout(conectar, 5000);
      };
      socket.onerror = () => socket?.close();
    };
    conectar();
    return () => {
      cerrado = true;
      if (reintento) clearTimeout(reintento);
      socket?.close();
    };
  }, [token, queryClient, alEvento]);
}

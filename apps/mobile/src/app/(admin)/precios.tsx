import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { View } from 'react-native';

import { Chips, Seccion, useCtrlEnter } from '@/components/admin/controles';
import { Boton } from '@/components/ui/Boton';
import { Campo } from '@/components/ui/Campo';
import { ErrorCarga, Pantalla } from '@/components/ui/Pantalla';
import { Tarjeta } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver, mensajeDeError, type Esquemas } from '@/lib/api';
import { useProductos, useSucursales } from '@/lib/consultas';
import { pesos } from '@/lib/formato';
import { useSesion } from '@/stores/sesion';

type Lista = Esquemas['Lista'];
type Turno = Esquemas['Turno'];
const LISTAS: Lista[] = ['mayorista', 'intermedio', 'minorista'];

/**
 * Listas de precios por producto × lista, para un turno y una zona (vacía = general). El precio
 * base del negocio es el pollo entero mayorista. Enter salta de campo; Ctrl+Enter guarda.
 */
export default function ListasDePrecios() {
  const queryClient = useQueryClient();
  const sucursalId = useSesion((s) => s.usuario?.sucursal_id ?? '');
  const [turno, setTurno] = useState<Turno>('manana');
  const [zona, setZona] = useState<string | null>(null);
  const [cambios, setCambios] = useState<Record<string, string>>({});
  const productos = useProductos();
  const sucursales = useSucursales();
  const zonas = useQuery({
    queryKey: ['zonas', sucursalId],
    enabled: !!sucursalId,
    queryFn: async () =>
      desenvolver(
        await api.GET('/sucursales/{sucursal_id}/zonas', {
          params: { path: { sucursal_id: sucursalId } },
        }),
      ),
  });
  const listas = useQuery({
    queryKey: ['listas', sucursalId, turno],
    enabled: !!sucursalId,
    queryFn: async () =>
      desenvolver(
        await api.GET('/precios/listas', { params: { query: { sucursal_id: sucursalId, turno } } }),
      ),
  });
  const guardar = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.PUT('/precios/listas', {
          body: {
            sucursal_id: sucursalId,
            precios: Object.entries(cambios)
              .filter(([, v]) => v.trim())
              .map(([clave, precio]) => {
                const [producto_codigo, lista] = clave.split('|') as [string, Lista];
                return {
                  producto_codigo,
                  lista,
                  turno,
                  zona_id: zona,
                  precio: precio.replace(',', '.'),
                };
              }),
          },
        }),
      ),
    onSuccess: () => {
      setCambios({});
      queryClient.invalidateQueries({ queryKey: ['listas'] });
      queryClient.invalidateQueries({ queryKey: ['cliente'] });
    },
  });
  const hayCambios = Object.values(cambios).some((v) => v.trim());
  useCtrlEnter(() => hayCambios && guardar.mutate(), hayCambios);

  const precioDe = (codigo: string, lista: Lista) =>
    (listas.data ?? []).find(
      (f) => f.producto_codigo === codigo && f.lista === lista && (f.zona_id ?? null) === zona,
    )?.precio ?? null;
  const general = (codigo: string, lista: Lista) =>
    (listas.data ?? []).find(
      (f) => f.producto_codigo === codigo && f.lista === lista && f.zona_id == null,
    )?.precio ?? null;

  return (
    <Pantalla sinNav refrescando={listas.isFetching} onRefrescar={() => listas.refetch()}>
      <Seccion
        titulo="Listas de precios"
        detalle={`Sucursal ${sucursales.data?.find((s) => s.id === sucursalId)?.nombre ?? ''} · precio base: pollo entero mayorista`}
        derecha={
          <Boton
            texto="Guardar (Ctrl+Enter)"
            icono="content-save"
            compacto
            onPress={() => guardar.mutate()}
            disabled={!hayCambios}
            cargando={guardar.isPending}
          />
        }>
        <Chips
          opciones={[
            { valor: 'manana', etiqueta: 'Mañana' },
            { valor: 'tarde', etiqueta: 'Tarde' },
          ]}
          valor={turno}
          onCambio={(v) => v && setTurno(v)}
          permitirNinguno={false}
        />
        <Chips
          opciones={(zonas.data ?? []).map((z) => ({ valor: z.id, etiqueta: z.nombre }))}
          valor={zona}
          onCambio={setZona}
        />
        <Texto variante="body-md" tono="suave">
          {zona
            ? 'Precios de la zona: pisan a los generales para los clientes de esa zona.'
            : 'Precios generales de la sucursal.'}
        </Texto>
      </Seccion>
      {listas.isError && !listas.data ? (
        <ErrorCarga error={listas.error} onReintentar={() => listas.refetch()} />
      ) : null}
      {guardar.isError ? (
        <Texto variante="body-md" tono="peligro">
          {mensajeDeError(guardar.error)}
        </Texto>
      ) : null}
      <Tarjeta>
        <View className="flex-row border-b border-border pb-2">
          <View className="w-[180px]">
            <Texto variante="label-caps" tono="suave">
              Producto
            </Texto>
          </View>
          {LISTAS.map((l) => (
            <View key={l} className="flex-1 px-1">
              <Texto variante="label-caps" tono="suave">
                {l}
              </Texto>
            </View>
          ))}
        </View>
        {(productos.data ?? []).map((p) => (
          <View key={p.codigo} className="flex-row items-center border-b border-border py-2">
            <View className="w-[180px]">
              <Texto variante="body-lg">{p.nombre}</Texto>
              {zona ? (
                <Texto variante="label-caps" tono="suave">
                  General:{' '}
                  {LISTAS.map((l) =>
                    general(p.codigo, l) ? pesos(general(p.codigo, l)) : '—',
                  ).join(' · ')}
                </Texto>
              ) : null}
            </View>
            {LISTAS.map((l) => {
              const clave = `${p.codigo}|${l}`;
              const actual = precioDe(p.codigo, l);
              return (
                <View key={l} className="flex-1 px-1">
                  <Campo
                    etiqueta=""
                    metrica
                    value={cambios[clave] ?? ''}
                    onChangeText={(v) => setCambios((c) => ({ ...c, [clave]: v }))}
                    placeholder={actual ?? 'sin precio'}
                    returnKeyType="next"
                  />
                </View>
              );
            })}
          </View>
        ))}
      </Tarjeta>
    </Pantalla>
  );
}

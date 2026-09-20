import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { View } from 'react-native';

import { Seccion } from '@/components/admin/controles';
import { Boton } from '@/components/ui/Boton';
import { Campo } from '@/components/ui/Campo';
import { Badge } from '@/components/ui/Estado';
import { Pantalla } from '@/components/ui/Pantalla';
import { Tarjeta } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver, mensajeDeError, type Esquemas } from '@/lib/api';
import { useSucursales } from '@/lib/consultas';
import { kilos } from '@/lib/formato';

function TarjetaSucursal({ sucursal }: { sucursal: Esquemas['SucursalSalida'] }) {
  const queryClient = useQueryClient();
  const [tara, setTara] = useState('');
  const [zona, setZona] = useState('');
  const zonas = useQuery({
    queryKey: ['zonas', sucursal.id],
    queryFn: async () =>
      desenvolver(
        await api.GET('/sucursales/{sucursal_id}/zonas', {
          params: { path: { sucursal_id: sucursal.id } },
        }),
      ),
  });
  const invalidar = () => {
    queryClient.invalidateQueries({ queryKey: ['sucursales'] });
    queryClient.invalidateQueries({ queryKey: ['zonas', sucursal.id] });
  };
  const guardarTara = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.PATCH('/sucursales/{sucursal_id}', {
          params: { path: { sucursal_id: sucursal.id } },
          body: { tara: tara.replace(',', '.') },
        }),
      ),
    onSuccess: () => {
      setTara('');
      invalidar();
    },
  });
  const crearZona = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.POST('/sucursales/{sucursal_id}/zonas', {
          params: { path: { sucursal_id: sucursal.id } },
          body: { nombre: zona },
        }),
      ),
    onSuccess: () => {
      setZona('');
      invalidar();
    },
  });
  const cambiarZona = useMutation({
    mutationFn: async ({ id, activa }: { id: string; activa: boolean }) =>
      desenvolver(
        await api.PATCH('/zonas/{zona_id}', {
          params: { path: { zona_id: id } },
          body: { activa },
        }),
      ),
    onSuccess: invalidar,
  });
  return (
    <Tarjeta elevada>
      <View className="flex-row items-center justify-between">
        <View>
          <Texto variante="headline-md">{sucursal.nombre}</Texto>
          <Texto variante="body-md" tono="suave">
            {sucursal.direccion || 'Sin dirección'}
          </Texto>
        </View>
        <Badge
          estado={sucursal.activa ? 'entregado' : 'cancelado'}
          texto={sucursal.activa ? 'Activa' : 'Baja'}
        />
      </View>
      <View className="mt-3 flex-row items-end gap-2">
        <View className="flex-1">
          <Campo
            etiqueta={`Tara por cajón (hoy ${kilos(sucursal.tara)})`}
            metrica
            value={tara}
            onChangeText={setTara}
            placeholder={sucursal.tara}
          />
        </View>
        <Boton
          texto="Guardar tara"
          compacto
          variante="secundario"
          icono="scale"
          onPress={() => guardarTara.mutate()}
          disabled={!tara.trim()}
          cargando={guardarTara.isPending}
        />
      </View>
      {guardarTara.isError ? (
        <Texto variante="body-md" tono="peligro">
          {mensajeDeError(guardarTara.error)}
        </Texto>
      ) : null}
      <Texto variante="label-caps" tono="suave" className="mt-4">
        Zonas de reparto
      </Texto>
      <View className="mt-1 flex-row flex-wrap gap-2">
        {(zonas.data ?? []).map((z) => (
          <View
            key={z.id}
            className={`flex-row items-center gap-1 rounded-pill border px-3 py-1 ${z.activa ? 'border-border bg-surface' : 'border-border bg-background opacity-60'}`}>
            <Texto variante="label-md">{z.nombre}</Texto>
            <Boton
              texto={z.activa ? 'Baja' : 'Alta'}
              variante="ghost"
              compacto
              onPress={() => cambiarZona.mutate({ id: z.id, activa: !z.activa })}
            />
          </View>
        ))}
        {zonas.data && zonas.data.length === 0 ? (
          <Texto variante="body-md" tono="suave">
            Sin zonas: los precios se cargan como generales.
          </Texto>
        ) : null}
      </View>
      <View className="mt-2 flex-row items-end gap-2">
        <View className="flex-1">
          <Campo
            etiqueta="Nueva zona"
            value={zona}
            onChangeText={setZona}
            placeholder="Norte, Este, Rivadavia…"
            onSubmitEditing={() => zona.trim().length >= 2 && crearZona.mutate()}
          />
        </View>
        <Boton
          texto="Agregar"
          compacto
          icono="plus"
          onPress={() => crearZona.mutate()}
          disabled={zona.trim().length < 2}
          cargando={crearZona.isPending}
        />
      </View>
      {crearZona.isError ? (
        <Texto variante="body-md" tono="peligro">
          {mensajeDeError(crearZona.error)}
        </Texto>
      ) : null}
    </Tarjeta>
  );
}

export default function Sucursales() {
  const queryClient = useQueryClient();
  const sucursales = useSucursales();
  const [nueva, setNueva] = useState({ nombre: '', direccion: '' });
  const crear = useMutation({
    mutationFn: async () => desenvolver(await api.POST('/sucursales', { body: nueva })),
    onSuccess: () => {
      setNueva({ nombre: '', direccion: '' });
      queryClient.invalidateQueries({ queryKey: ['sucursales'] });
    },
  });
  return (
    <Pantalla sinNav refrescando={sucursales.isFetching} onRefrescar={() => sucursales.refetch()}>
      <Seccion
        titulo="Sucursales"
        detalle="Granja, planta y sucursales: todo reporte se filtra por sucursal">
        {(sucursales.data ?? []).map((s) => (
          <TarjetaSucursal key={s.id} sucursal={s} />
        ))}
        <Tarjeta>
          <Texto variante="headline-md">Nueva sucursal</Texto>
          <View className="mt-2 flex-row flex-wrap items-end gap-2">
            <View className="min-w-[160px] flex-1">
              <Campo
                etiqueta="Nombre"
                value={nueva.nombre}
                onChangeText={(v) => setNueva({ ...nueva, nombre: v })}
              />
            </View>
            <View className="min-w-[200px] flex-[2]">
              <Campo
                etiqueta="Dirección"
                value={nueva.direccion}
                onChangeText={(v) => setNueva({ ...nueva, direccion: v })}
              />
            </View>
            <Boton
              texto="Crear"
              compacto
              icono="store-plus"
              onPress={() => crear.mutate()}
              disabled={nueva.nombre.trim().length < 2}
              cargando={crear.isPending}
            />
          </View>
          {crear.isError ? (
            <Texto variante="body-md" tono="peligro">
              {mensajeDeError(crear.error)}
            </Texto>
          ) : null}
        </Tarjeta>
      </Seccion>
    </Pantalla>
  );
}

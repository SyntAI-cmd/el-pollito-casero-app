import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';

import { Seccion, Tabla } from '@/components/admin/controles';
import { Boton } from '@/components/ui/Boton';
import { Campo } from '@/components/ui/Campo';
import { Badge } from '@/components/ui/Estado';
import { ErrorCarga, Pantalla } from '@/components/ui/Pantalla';
import { Tarjeta } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver, mensajeDeError, type Cliente } from '@/lib/api';
import { useClientes } from '@/lib/consultas';
import { ETIQUETA_TURNO } from '@/lib/formato';

const ESTADO_FICHA = { completa: 'entregado', sin_cuit: 'deuda', revisar: 'pendiente' } as const;
const ETIQUETA_FICHA = { completa: 'Completa', sin_cuit: 'Sin CUIT', revisar: 'Revisar' };

export default function Clientes() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [q, setQ] = useState('');
  const [nuevo, setNuevo] = useState<{
    razon_social: string;
    nombre_comercial: string;
    cuit: string;
    telefono: string;
    direccion: string;
    localidad: string;
  } | null>(null);
  const clientes = useClientes(q.trim());
  const crear = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.POST('/clientes', {
          body: {
            razon_social: nuevo!.razon_social,
            nombre_comercial: nuevo!.nombre_comercial || null,
            cuit: nuevo!.cuit || null,
            telefono: nuevo!.telefono || null,
            direccion: nuevo!.direccion,
            localidad: nuevo!.localidad,
          },
        }),
      ),
    onSuccess: (c) => {
      setNuevo(null);
      queryClient.invalidateQueries({ queryKey: ['clientes'] });
      router.push({ pathname: '/(admin)/clientes/[id]', params: { id: c.id } });
    },
  });

  return (
    <Pantalla sinNav refrescando={clientes.isFetching} onRefrescar={() => clientes.refetch()}>
      <Seccion
        titulo="Clientes"
        detalle="Fichas al estilo GC/Atuq: precios propios, extracto y envases"
        derecha={
          <Boton
            texto="Nuevo cliente"
            icono="account-plus"
            compacto
            onPress={() =>
              setNuevo({
                razon_social: '',
                nombre_comercial: '',
                cuit: '',
                telefono: '',
                direccion: '',
                localidad: 'San Martín',
              })
            }
          />
        }>
        <Campo
          etiqueta="Buscar"
          value={q}
          onChangeText={setQ}
          placeholder="Nombre, razón social, CUIT, código o teléfono"
          autoFocus
        />
      </Seccion>
      {nuevo ? (
        <Tarjeta elevada>
          <Texto variante="headline-md">Nuevo cliente</Texto>
          <View className="mt-2 gap-2">
            <Campo
              etiqueta="Razón social"
              value={nuevo.razon_social}
              onChangeText={(v) => setNuevo({ ...nuevo, razon_social: v })}
              autoFocus
            />
            <Campo
              etiqueta="Nombre comercial (apodo)"
              value={nuevo.nombre_comercial}
              onChangeText={(v) => setNuevo({ ...nuevo, nombre_comercial: v })}
            />
            <View className="flex-row gap-2">
              <View className="flex-1">
                <Campo
                  etiqueta="CUIT"
                  value={nuevo.cuit}
                  onChangeText={(v) => setNuevo({ ...nuevo, cuit: v })}
                />
              </View>
              <View className="flex-1">
                <Campo
                  etiqueta="Teléfono"
                  value={nuevo.telefono}
                  onChangeText={(v) => setNuevo({ ...nuevo, telefono: v })}
                  keyboardType="phone-pad"
                />
              </View>
            </View>
            <Campo
              etiqueta="Dirección"
              value={nuevo.direccion}
              onChangeText={(v) => setNuevo({ ...nuevo, direccion: v })}
            />
            <Campo
              etiqueta="Localidad"
              value={nuevo.localidad}
              onChangeText={(v) => setNuevo({ ...nuevo, localidad: v })}
            />
            <View className="flex-row gap-2">
              <View className="flex-1">
                <Boton texto="Cancelar" variante="ghost" onPress={() => setNuevo(null)} />
              </View>
              <View className="flex-1">
                <Boton
                  texto="Crear ficha"
                  icono="check"
                  onPress={() => crear.mutate()}
                  disabled={nuevo.razon_social.trim().length < 2}
                  cargando={crear.isPending}
                />
              </View>
            </View>
            {crear.isError ? (
              <Texto variante="body-md" tono="peligro">
                {mensajeDeError(crear.error)}
              </Texto>
            ) : null}
          </View>
        </Tarjeta>
      ) : null}
      {clientes.isError && !clientes.data ? (
        <ErrorCarga error={clientes.error} onReintentar={() => clientes.refetch()} />
      ) : null}
      <Tabla<Cliente>
        columnas={[
          {
            clave: 'codigo',
            titulo: 'Código',
            ancho: 90,
            render: (c) => <Texto variante="body-metric">{c.codigo ?? '—'}</Texto>,
          },
          {
            clave: 'nombre',
            titulo: 'Cliente',
            ancho: 220,
            render: (c) => (
              <Texto variante="body-lg" numberOfLines={1}>
                {c.nombre_comercial}
              </Texto>
            ),
          },
          {
            clave: 'razon',
            titulo: 'Razón social',
            ancho: 200,
            render: (c) => (
              <Texto variante="body-md" numberOfLines={1}>
                {c.razon_social}
              </Texto>
            ),
          },
          {
            clave: 'cuit',
            titulo: 'CUIT',
            ancho: 130,
            render: (c) => <Texto variante="body-metric">{c.cuit ?? '—'}</Texto>,
          },
          {
            clave: 'direccion',
            titulo: 'Dirección',
            ancho: 220,
            render: (c) => (
              <Texto variante="body-md" numberOfLines={1}>
                {c.direccion} {c.localidad}
              </Texto>
            ),
          },
          {
            clave: 'lista',
            titulo: 'Lista · turno',
            ancho: 150,
            render: (c) => (
              <Texto variante="body-md">
                {c.lista} · {ETIQUETA_TURNO[c.turno]}
              </Texto>
            ),
          },
          {
            clave: 'ficha',
            titulo: 'Ficha',
            ancho: 110,
            render: (c) => (
              <Badge estado={ESTADO_FICHA[c.estado_ficha]} texto={ETIQUETA_FICHA[c.estado_ficha]} />
            ),
          },
        ]}
        filas={clientes.data ?? []}
        claveDe={(c) => c.id}
        onFila={(c) => router.push({ pathname: '/(admin)/clientes/[id]', params: { id: c.id } })}
      />
    </Pantalla>
  );
}

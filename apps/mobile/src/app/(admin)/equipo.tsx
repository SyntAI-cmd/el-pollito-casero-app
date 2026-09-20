import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { View } from 'react-native';

import { Chips, Seccion, Tabla } from '@/components/admin/controles';
import { Boton } from '@/components/ui/Boton';
import { Campo } from '@/components/ui/Campo';
import { Badge } from '@/components/ui/Estado';
import { Pantalla } from '@/components/ui/Pantalla';
import { Tarjeta } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver, mensajeDeError, type Esquemas, type Usuario } from '@/lib/api';
import { useUsuarios } from '@/lib/consultas';
import { useSesion } from '@/stores/sesion';

type Rol = Esquemas['Rol'];
type Vehiculo = Esquemas['VehiculoSalida'];
const ROLES: { valor: Rol; etiqueta: string }[] = [
  { valor: 'preventista', etiqueta: 'Preventista' },
  { valor: 'cobrador', etiqueta: 'Cobrador' },
  { valor: 'admin', etiqueta: 'Administración' },
];

export default function Equipo() {
  const queryClient = useQueryClient();
  const sucursalId = useSesion((s) => s.usuario?.sucursal_id ?? '');
  const usuarios = useUsuarios();
  const vehiculos = useQuery({
    queryKey: ['vehiculos', 'todos'],
    queryFn: async () =>
      desenvolver(await api.GET('/vehiculos', { params: { query: { incluir_inactivos: true } } })),
  });
  const [nuevo, setNuevo] = useState({
    nombre: '',
    usuario: '',
    clave: '',
    rol: 'preventista' as Rol,
    telefono: '',
    cuit: '',
  });
  const [claveNueva, setClaveNueva] = useState<{ id: string; clave: string } | null>(null);
  const [vehiculo, setVehiculo] = useState({ nombre: '', patente: '', nota: '' });

  const invalidar = () => {
    queryClient.invalidateQueries({ queryKey: ['usuarios'] });
    queryClient.invalidateQueries({ queryKey: ['vehiculos'] });
  };
  const crearUsuario = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.POST('/usuarios', {
          body: {
            ...nuevo,
            sucursal_id: sucursalId,
            telefono: nuevo.telefono || null,
            cuit: nuevo.cuit || null,
          },
        }),
      ),
    onSuccess: () => {
      setNuevo({ nombre: '', usuario: '', clave: '', rol: 'preventista', telefono: '', cuit: '' });
      invalidar();
    },
  });
  const modificarUsuario = useMutation({
    mutationFn: async ({ id, cambios }: { id: string; cambios: Esquemas['UsuarioCambios'] }) =>
      desenvolver(
        await api.PATCH('/usuarios/{usuario_id}', {
          params: { path: { usuario_id: id } },
          body: cambios,
        }),
      ),
    onSuccess: () => {
      setClaveNueva(null);
      invalidar();
    },
  });
  const crearVehiculo = useMutation({
    mutationFn: async () => desenvolver(await api.POST('/vehiculos', { body: vehiculo })),
    onSuccess: () => {
      setVehiculo({ nombre: '', patente: '', nota: '' });
      invalidar();
    },
  });
  const modificarVehiculo = useMutation({
    mutationFn: async ({ id, activo }: { id: string; activo: boolean }) =>
      desenvolver(
        await api.PATCH('/vehiculos/{vehiculo_id}', {
          params: { path: { vehiculo_id: id } },
          body: { activo },
        }),
      ),
    onSuccess: invalidar,
  });

  return (
    <Pantalla sinNav refrescando={usuarios.isFetching} onRefrescar={() => usuarios.refetch()}>
      <Seccion titulo="Equipo" detalle="Cada preventista y cobrador entra con su usuario">
        <Tabla<Usuario>
          columnas={[
            {
              clave: 'nombre',
              titulo: 'Nombre',
              ancho: 180,
              render: (u) => <Texto variante="body-lg">{u.nombre}</Texto>,
            },
            {
              clave: 'usuario',
              titulo: 'Usuario',
              ancho: 140,
              render: (u) => <Texto variante="body-metric">{u.usuario}</Texto>,
            },
            {
              clave: 'rol',
              titulo: 'Rol',
              ancho: 120,
              render: (u) => <Texto variante="body-md">{u.rol}</Texto>,
            },
            {
              clave: 'telefono',
              titulo: 'Teléfono',
              ancho: 140,
              render: (u) => <Texto variante="body-metric">{u.telefono ?? '—'}</Texto>,
            },
            {
              clave: 'estado',
              titulo: 'Estado',
              ancho: 100,
              render: (u) => (
                <Badge
                  estado={u.activo ? 'entregado' : 'cancelado'}
                  texto={u.activo ? 'Activo' : 'Baja'}
                />
              ),
            },
            {
              clave: 'acciones',
              titulo: 'Acciones',
              ancho: 360,
              render: (u) => (
                <View className="flex-row items-center gap-1">
                  {claveNueva?.id === u.id ? (
                    <>
                      <View className="w-[160px]">
                        <Campo
                          etiqueta=""
                          value={claveNueva.clave}
                          onChangeText={(clave) => setClaveNueva({ id: u.id, clave })}
                          placeholder="Clave nueva"
                          secureTextEntry
                        />
                      </View>
                      <Boton
                        texto="Guardar"
                        compacto
                        onPress={() =>
                          modificarUsuario.mutate({
                            id: u.id,
                            cambios: { clave: claveNueva.clave },
                          })
                        }
                        disabled={claveNueva.clave.length < 6}
                      />
                    </>
                  ) : (
                    <Boton
                      texto="Cambiar clave"
                      variante="ghost"
                      compacto
                      onPress={() => setClaveNueva({ id: u.id, clave: '' })}
                    />
                  )}
                  <Boton
                    texto={u.activo ? 'Dar de baja' : 'Reactivar'}
                    variante="ghost"
                    compacto
                    onPress={() =>
                      modificarUsuario.mutate({ id: u.id, cambios: { activo: !u.activo } })
                    }
                  />
                </View>
              ),
            },
          ]}
          filas={usuarios.data ?? []}
          claveDe={(u) => u.id}
        />
        {modificarUsuario.isError ? (
          <Texto variante="body-md" tono="peligro">
            {mensajeDeError(modificarUsuario.error)}
          </Texto>
        ) : null}
        <Tarjeta>
          <Texto variante="headline-md">Nuevo usuario</Texto>
          <View className="mt-2 gap-2">
            <View className="flex-row gap-2">
              <View className="flex-1">
                <Campo
                  etiqueta="Nombre"
                  value={nuevo.nombre}
                  onChangeText={(v) => setNuevo({ ...nuevo, nombre: v })}
                />
              </View>
              <View className="flex-1">
                <Campo
                  etiqueta="Usuario (minúsculas)"
                  value={nuevo.usuario}
                  onChangeText={(v) =>
                    setNuevo({ ...nuevo, usuario: v.toLowerCase().replace(/[^a-z0-9._-]/g, '') })
                  }
                  autoCapitalize="none"
                />
              </View>
            </View>
            <View className="flex-row gap-2">
              <View className="flex-1">
                <Campo
                  etiqueta="Clave"
                  value={nuevo.clave}
                  onChangeText={(v) => setNuevo({ ...nuevo, clave: v })}
                  secureTextEntry
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
              <View className="flex-1">
                <Campo
                  etiqueta="CUIT"
                  value={nuevo.cuit}
                  onChangeText={(v) => setNuevo({ ...nuevo, cuit: v })}
                />
              </View>
            </View>
            <Chips
              opciones={ROLES}
              valor={nuevo.rol}
              onCambio={(v) => v && setNuevo({ ...nuevo, rol: v })}
              permitirNinguno={false}
            />
            <Boton
              texto="Crear usuario"
              icono="account-plus"
              onPress={() => crearUsuario.mutate()}
              disabled={
                nuevo.nombre.trim().length < 2 || nuevo.usuario.length < 2 || nuevo.clave.length < 6
              }
              cargando={crearUsuario.isPending}
            />
            {crearUsuario.isError ? (
              <Texto variante="body-md" tono="peligro">
                {mensajeDeError(crearUsuario.error)}
              </Texto>
            ) : null}
          </View>
        </Tarjeta>
      </Seccion>
      <Seccion titulo="Vehículos">
        <Tabla<Vehiculo>
          columnas={[
            {
              clave: 'nombre',
              titulo: 'Vehículo',
              ancho: 180,
              render: (v) => <Texto variante="body-lg">{v.nombre}</Texto>,
            },
            {
              clave: 'patente',
              titulo: 'Patente',
              ancho: 110,
              render: (v) => <Texto variante="body-metric">{v.patente}</Texto>,
            },
            {
              clave: 'nota',
              titulo: 'Nota',
              ancho: 200,
              render: (v) => <Texto variante="body-md">{v.nota}</Texto>,
            },
            {
              clave: 'estado',
              titulo: 'Estado',
              ancho: 100,
              render: (v) => (
                <Badge
                  estado={v.activo ? 'entregado' : 'cancelado'}
                  texto={v.activo ? 'Activo' : 'Baja'}
                />
              ),
            },
            {
              clave: 'acciones',
              titulo: '',
              ancho: 140,
              render: (v) => (
                <Boton
                  texto={v.activo ? 'Dar de baja' : 'Reactivar'}
                  variante="ghost"
                  compacto
                  onPress={() => modificarVehiculo.mutate({ id: v.id, activo: !v.activo })}
                />
              ),
            },
          ]}
          filas={vehiculos.data ?? []}
          claveDe={(v) => v.id}
        />
        <Tarjeta>
          <Texto variante="headline-md">Nuevo vehículo</Texto>
          <View className="mt-2 flex-row flex-wrap items-end gap-2">
            <View className="min-w-[160px] flex-1">
              <Campo
                etiqueta="Nombre"
                value={vehiculo.nombre}
                onChangeText={(v) => setVehiculo({ ...vehiculo, nombre: v })}
                placeholder="Toyota Hino"
              />
            </View>
            <View className="min-w-[120px] flex-1">
              <Campo
                etiqueta="Patente"
                value={vehiculo.patente}
                onChangeText={(v) => setVehiculo({ ...vehiculo, patente: v.toUpperCase() })}
                autoCapitalize="characters"
              />
            </View>
            <View className="min-w-[160px] flex-1">
              <Campo
                etiqueta="Nota"
                value={vehiculo.nota}
                onChangeText={(v) => setVehiculo({ ...vehiculo, nota: v })}
                placeholder="Camión"
              />
            </View>
            <Boton
              texto="Agregar"
              icono="truck-plus"
              compacto
              onPress={() => crearVehiculo.mutate()}
              disabled={vehiculo.nombre.length < 2 || vehiculo.patente.length < 5}
              cargando={crearVehiculo.isPending}
            />
          </View>
          {crearVehiculo.isError ? (
            <Texto variante="body-md" tono="peligro">
              {mensajeDeError(crearVehiculo.error)}
            </Texto>
          ) : null}
        </Tarjeta>
      </Seccion>
    </Pantalla>
  );
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Linking, View } from 'react-native';

import { Chips, Seccion, SelectorFecha } from '@/components/admin/controles';
import { Mapa } from '@/components/Mapa';
import { Boton } from '@/components/ui/Boton';
import { Campo } from '@/components/ui/Campo';
import { Badge } from '@/components/ui/Estado';
import { ErrorCarga, Pantalla, Vacio } from '@/components/ui/Pantalla';
import { Tarjeta } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver, mensajeDeError, type Salida } from '@/lib/api';
import { useSalidas, useUsuarios } from '@/lib/consultas';
import { horaCorta, hoyIso } from '@/lib/formato';

function TarjetaSalida({ salida }: { salida: Salida }) {
  const queryClient = useQueryClient();
  const [motivo, setMotivo] = useState('');
  const recorrido = useQuery({
    queryKey: ['recorrido', salida.id],
    enabled: !!salida.ultima_posicion,
    refetchInterval: 30_000,
    queryFn: async () =>
      desenvolver(
        await api.GET('/salidas/{salida_id}/recorrido', {
          params: { path: { salida_id: salida.id } },
        }),
      ),
  });
  const cerrar = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.POST('/salidas/{salida_id}/cerrar', {
          params: { path: { salida_id: salida.id } },
          body: { motivo: motivo.trim() || null },
        }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['salidas'] });
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
    },
  });
  const posicion = salida.ultima_posicion;
  return (
    <Tarjeta elevada>
      <View className="flex-row items-start justify-between">
        <View>
          <Texto variante="headline-md">
            {salida.vehiculo_nombre} · {salida.vehiculo_patente}
          </Texto>
          <Texto variante="body-md" tono="suave">
            {salida.preventista_nombre}
            {salida.segundo_preventista_nombre
              ? ` y ${salida.segundo_preventista_nombre}`
              : ''} · {salida.pedidos} pedidos · {salida.pedidos_entregados} entregados
          </Texto>
        </View>
        <Badge
          estado={salida.cerrada_en ? 'en_camino' : 'pendiente'}
          texto={salida.cerrada_en ? `Salió ${salida.hora_salida?.slice(0, 5) ?? ''}` : 'Sin salir'}
        />
      </View>
      {posicion ? (
        <View className="mt-3 gap-2">
          <Mapa
            puntos={[
              {
                lat: Number(posicion.lat),
                lng: Number(posicion.lng),
                titulo: salida.vehiculo_nombre,
                tipo: 'camion',
              },
            ]}
            recorrido={(recorrido.data ?? []).map((p) => ({
              lat: Number(p.lat),
              lng: Number(p.lng),
            }))}
            alto={220}
          />
          <View className="flex-row items-center justify-between">
            <Texto variante="body-md" tono="suave">
              Última posición {horaCorta(posicion.registrado_en)}
              {posicion.velocidad ? ` · ${Number(posicion.velocidad).toFixed(0)} km/h` : ''}
            </Texto>
            <Boton
              texto="Abrir en Google Maps"
              variante="ghost"
              compacto
              icono="open-in-new"
              onPress={() =>
                Linking.openURL(
                  `https://www.google.com/maps/search/?api=1&query=${posicion.lat},${posicion.lng}`,
                )
              }
            />
          </View>
        </View>
      ) : (
        <Texto variante="body-md" tono="suave" className="mt-2">
          Sin posición todavía: el repartidor activa «Compartir ubicación» en su inicio de reparto.
        </Texto>
      )}
      {!salida.cerrada_en ? (
        <View className="mt-3 gap-2">
          {salida.faltantes.length ? (
            <Texto variante="body-md" tono="peligro">
              Falta pesar o cargar:{' '}
              {salida.faltantes
                .map((f) => `#${f.numero} (${f.sin_pesar} sin pesar, ${f.sin_cargar} sin cargar)`)
                .join(', ')}
            </Texto>
          ) : null}
          {salida.faltantes.length ? (
            <Campo etiqueta="Motivo para salir igual" value={motivo} onChangeText={setMotivo} />
          ) : null}
          <Boton
            texto="Cerrar camión"
            icono="truck-fast"
            variante="secundario"
            onPress={() => cerrar.mutate()}
            disabled={
              salida.pedidos === 0 || (salida.faltantes.length > 0 && motivo.trim().length < 3)
            }
            cargando={cerrar.isPending}
          />
          {cerrar.isError ? (
            <Texto variante="body-md" tono="peligro">
              {mensajeDeError(cerrar.error)}
            </Texto>
          ) : null}
        </View>
      ) : null}
    </Tarjeta>
  );
}

export default function FlotaEnVivo() {
  const queryClient = useQueryClient();
  const [fecha, setFecha] = useState(hoyIso());
  const [vehiculo, setVehiculo] = useState<string | null>(null);
  const [preventista, setPreventista] = useState<string | null>(null);
  const [segundo, setSegundo] = useState<string | null>(null);
  const salidas = useSalidas(fecha);
  const usuarios = useUsuarios();
  const vehiculos = useQuery({
    queryKey: ['vehiculos'],
    queryFn: async () => desenvolver(await api.GET('/vehiculos')),
  });
  const armar = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.PUT('/salidas', {
          body: {
            vehiculo_id: vehiculo!,
            fecha,
            preventista_id: preventista!,
            segundo_preventista_id: segundo,
          },
        }),
      ),
    onSuccess: () => {
      setVehiculo(null);
      setPreventista(null);
      setSegundo(null);
      queryClient.invalidateQueries({ queryKey: ['salidas'] });
    },
  });
  const preventistas = (usuarios.data ?? []).filter((u) => u.rol === 'preventista' && u.activo);
  const todos = (salidas.data ?? []).filter((s) => s.ultima_posicion);

  return (
    <Pantalla sinNav refrescando={salidas.isFetching} onRefrescar={() => salidas.refetch()}>
      <SelectorFecha valor={fecha} onCambio={setFecha} />
      {todos.length > 1 ? (
        <Mapa
          puntos={todos.map((s) => ({
            lat: Number(s.ultima_posicion!.lat),
            lng: Number(s.ultima_posicion!.lng),
            titulo: `${s.vehiculo_nombre} · ${s.preventista_nombre}`,
            tipo: 'camion' as const,
          }))}
          alto={280}
        />
      ) : null}
      {salidas.isError && !salidas.data ? (
        <ErrorCarga error={salidas.error} onReintentar={() => salidas.refetch()} />
      ) : null}
      {salidas.data && salidas.data.length === 0 ? (
        <Vacio
          icono="truck"
          titulo="Sin salidas armadas"
          detalle="Armá la salida del día: vehículo + hasta dos preventistas."
        />
      ) : null}
      {(salidas.data ?? []).map((s) => (
        <TarjetaSalida key={s.id} salida={s} />
      ))}
      <Seccion titulo="Armar salida" detalle="Un preventista va en un solo vehículo por día">
        <Tarjeta>
          <Texto variante="label-md" tono="suave">
            Vehículo
          </Texto>
          <Chips
            opciones={(vehiculos.data ?? []).map((v) => ({
              valor: v.id,
              etiqueta: `${v.nombre} ${v.patente}`,
            }))}
            valor={vehiculo}
            onCambio={setVehiculo}
          />
          <Texto variante="label-md" tono="suave" className="mt-2">
            Preventista
          </Texto>
          <Chips
            opciones={preventistas.map((u) => ({ valor: u.id, etiqueta: u.nombre }))}
            valor={preventista}
            onCambio={setPreventista}
          />
          <Texto variante="label-md" tono="suave" className="mt-2">
            Segundo preventista
          </Texto>
          <Chips
            opciones={preventistas
              .filter((u) => u.id !== preventista)
              .map((u) => ({ valor: u.id, etiqueta: u.nombre }))}
            valor={segundo}
            onCambio={setSegundo}
          />
          <View className="mt-3">
            <Boton
              texto="Guardar salida"
              icono="truck"
              onPress={() => armar.mutate()}
              disabled={!vehiculo || !preventista}
              cargando={armar.isPending}
            />
          </View>
          {armar.isError ? (
            <Texto variante="body-md" tono="peligro">
              {mensajeDeError(armar.error)}
            </Texto>
          ) : null}
        </Tarjeta>
      </Seccion>
    </Pantalla>
  );
}

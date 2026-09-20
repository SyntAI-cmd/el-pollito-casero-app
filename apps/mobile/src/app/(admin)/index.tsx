import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { Chips, Seccion, SelectorFecha, Tabla } from '@/components/admin/controles';
import { Boton } from '@/components/ui/Boton';
import { Campo } from '@/components/ui/Campo';
import { Badge } from '@/components/ui/Estado';
import { ErrorCarga, Pantalla, Vacio } from '@/components/ui/Pantalla';
import { GrillaAccesos, MetricaHero, Tarjeta } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver, mensajeDeError, type Pedido } from '@/lib/api';
import { useNotaDelDia } from '@/lib/consultas';
import { ETIQUETA_TURNO, hoyIso, kilos, pesos } from '@/lib/formato';
import { tokens } from '@/theme/tokens';

function Noticias() {
  const queryClient = useQueryClient();
  const [titulo, setTitulo] = useState('');
  const noticias = useQuery({
    queryKey: ['noticias'],
    queryFn: async () => desenvolver(await api.GET('/noticias')),
  });
  const publicar = useMutation({
    mutationFn: async () =>
      desenvolver(await api.POST('/noticias', { body: { titulo, fijada: false } })),
    onSuccess: () => {
      setTitulo('');
      queryClient.invalidateQueries({ queryKey: ['noticias'] });
    },
  });
  const cambiar = useMutation({
    mutationFn: async ({
      id,
      cambios,
    }: {
      id: string;
      cambios: { fijada?: boolean; archivada?: boolean };
    }) =>
      desenvolver(
        await api.PATCH('/noticias/{noticia_id}', {
          params: { path: { noticia_id: id } },
          body: cambios,
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['noticias'] }),
  });
  return (
    <Tarjeta>
      <Texto variante="label-caps" tono="suave">
        Noticias del equipo
      </Texto>
      {(noticias.data ?? []).map((n) => (
        <View
          key={n.id}
          className="mt-2 flex-row items-center gap-2 rounded-input bg-background px-3 py-2">
          <MaterialCommunityIcons
            name={n.fijada ? 'pin' : 'bullhorn'}
            size={18}
            color={tokens.colors.primary}
          />
          <View className="flex-1">
            <Texto variante="body-lg">{n.titulo}</Texto>
            {n.cuerpo ? (
              <Texto variante="body-md" tono="suave">
                {n.cuerpo}
              </Texto>
            ) : null}
          </View>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={n.fijada ? 'Desfijar' : 'Fijar'}
            onPress={() => cambiar.mutate({ id: n.id, cambios: { fijada: !n.fijada } })}
            className="h-12 w-12 items-center justify-center">
            <MaterialCommunityIcons
              name={n.fijada ? 'pin-off' : 'pin'}
              size={20}
              color={tokens.colors['on-surface-v']}
            />
          </Pressable>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Archivar"
            onPress={() => cambiar.mutate({ id: n.id, cambios: { archivada: true } })}
            className="h-12 w-12 items-center justify-center">
            <MaterialCommunityIcons
              name="archive-arrow-down"
              size={20}
              color={tokens.colors['on-surface-v']}
            />
          </Pressable>
        </View>
      ))}
      <View className="mt-3 flex-row items-end gap-2">
        <View className="flex-1">
          <Campo
            etiqueta="Nueva noticia"
            value={titulo}
            onChangeText={setTitulo}
            placeholder="Ej.: mañana no hay reparto a La Paz"
            onSubmitEditing={() => titulo.trim().length >= 2 && publicar.mutate()}
            returnKeyType="send"
          />
        </View>
        <Boton
          texto="Publicar"
          icono="bullhorn"
          compacto
          onPress={() => publicar.mutate()}
          disabled={titulo.trim().length < 2}
          cargando={publicar.isPending}
        />
      </View>
      {publicar.isError ? (
        <Texto variante="body-md" tono="peligro">
          {mensajeDeError(publicar.error)}
        </Texto>
      ) : null}
    </Tarjeta>
  );
}

export default function NotaDelDia() {
  const router = useRouter();
  const [fecha, setFecha] = useState(hoyIso());
  const [turno, setTurno] = useState<'manana' | 'tarde' | null>(null);
  const nota = useNotaDelDia(fecha);
  const n = nota.data;
  const grupos = (n?.por_preventista ?? []).map((g) => ({
    ...g,
    pedidos: turno ? g.pedidos.filter((p) => p.turno === turno) : g.pedidos,
  }));

  return (
    <Pantalla sinNav refrescando={nota.isFetching} onRefrescar={() => nota.refetch()}>
      <SelectorFecha valor={fecha} onCambio={setFecha} />
      <Chips
        opciones={[
          { valor: 'manana', etiqueta: 'Mañana' },
          { valor: 'tarde', etiqueta: 'Tarde' },
        ]}
        valor={turno}
        onCambio={setTurno}
      />
      <Noticias />
      {nota.isError && !n ? (
        <ErrorCarga error={nota.error} onReintentar={() => nota.refetch()} />
      ) : null}
      {n ? (
        <>
          <View className="flex-row flex-wrap gap-3">
            <View className="min-w-[280px] flex-1">
              <MetricaHero
                etiqueta="Pedidos del día"
                valor={`${n.cantidad_pedidos}`}
                detalle={`${n.cajones} cajones · ${kilos(n.kilos)}`}
              />
            </View>
            <View className="min-w-[280px] flex-1">
              <MetricaHero
                etiqueta="Importe pesado"
                valor={pesos(n.importe)}
                detalle="Solo lo que ya pasó por la balanza"
              />
            </View>
          </View>
          <GrillaAccesos
            accesos={[
              {
                icono: 'cart-plus',
                subtitulo: 'Nota',
                titulo: 'Cargar pedido',
                onPress: () => router.push('/(admin)/nuevo-pedido'),
              },
              {
                icono: 'scale',
                subtitulo: 'Piso',
                titulo: 'Balanza',
                onPress: () => router.push('/(reparto)/pesada'),
              },
              {
                icono: 'truck-check',
                subtitulo: 'Piso',
                titulo: 'Carga',
                onPress: () => router.push('/(reparto)/carga'),
              },
              {
                icono: 'printer',
                subtitulo: 'Papel',
                titulo: 'Imprimir',
                onPress: () => router.push('/(admin)/imprimir'),
              },
            ]}
          />
          <Seccion titulo="Totales por producto" detalle="Lo que hay que faenar y pesar">
            <Tabla
              columnas={[
                {
                  clave: 'producto',
                  titulo: 'Producto',
                  ancho: 200,
                  render: (t) => <Texto variante="body-lg">{t.producto_nombre}</Texto>,
                },
                {
                  clave: 'cajas',
                  titulo: 'Cajas',
                  ancho: 90,
                  alinear: 'derecha',
                  render: (t) => <Texto variante="body-metric">{t.cajas}</Texto>,
                },
                {
                  clave: 'kg_pedidos',
                  titulo: 'Kg pedidos',
                  ancho: 120,
                  alinear: 'derecha',
                  render: (t) => <Texto variante="body-metric">{kilos(t.kg_pedidos)}</Texto>,
                },
                {
                  clave: 'kg_pesados',
                  titulo: 'Kg pesados',
                  ancho: 120,
                  alinear: 'derecha',
                  render: (t) => <Texto variante="body-metric">{kilos(t.kg_pesados)}</Texto>,
                },
                {
                  clave: 'pedidos',
                  titulo: 'Pedidos',
                  ancho: 90,
                  alinear: 'derecha',
                  render: (t) => <Texto variante="body-metric">{t.pedidos}</Texto>,
                },
              ]}
              filas={n.por_producto}
              claveDe={(t) => t.producto_codigo}
            />
          </Seccion>
          {n.cantidad_pedidos === 0 ? (
            <Vacio
              icono="inbox"
              titulo="Sin pedidos para esta fecha"
              detalle="Cargá el primero desde Cargar pedido."
            />
          ) : null}
          {grupos.map((g) => (
            <Seccion
              key={g.preventista_id ?? 'sin'}
              titulo={g.preventista_nombre}
              detalle={`${g.pedidos.length} pedidos · ${g.cajones} cajones · ${kilos(g.kilos)} · ${pesos(g.importe)}`}>
              <Tabla<Pedido>
                columnas={[
                  {
                    clave: 'numero',
                    titulo: 'N°',
                    ancho: 80,
                    render: (p) => <Texto variante="body-metric">{p.numero}</Texto>,
                  },
                  {
                    clave: 'cliente',
                    titulo: 'Cliente',
                    ancho: 220,
                    render: (p) => (
                      <Texto variante="body-lg" numberOfLines={1}>
                        {p.cliente_nombre}
                      </Texto>
                    ),
                  },
                  {
                    clave: 'turno',
                    titulo: 'Turno',
                    ancho: 90,
                    render: (p) => <Texto variante="body-md">{ETIQUETA_TURNO[p.turno]}</Texto>,
                  },
                  {
                    clave: 'detalle',
                    titulo: 'Detalle',
                    ancho: 320,
                    render: (p) => (
                      <Texto variante="body-md" numberOfLines={1}>
                        {p.items
                          .map(
                            (i) =>
                              `${i.cajas ? `${i.cajas}× ` : ''}${i.producto_nombre}${i.kg_pedidos ? ` ${kilos(i.kg_pedidos)}` : ''}`,
                          )
                          .join(' · ')}
                      </Texto>
                    ),
                  },
                  {
                    clave: 'cajones',
                    titulo: 'Cajones',
                    ancho: 90,
                    alinear: 'derecha',
                    render: (p) => (
                      <Texto variante="body-metric">
                        {p.cajones_cargados}/{p.cajones}
                      </Texto>
                    ),
                  },
                  {
                    clave: 'total',
                    titulo: 'Total',
                    ancho: 120,
                    alinear: 'derecha',
                    render: (p) => (
                      <Texto variante="body-metric">
                        {p.sin_pesar.length ? '—' : pesos(p.total)}
                      </Texto>
                    ),
                  },
                  {
                    clave: 'estado',
                    titulo: 'Estado',
                    ancho: 140,
                    render: (p) => <Badge estado={p.estado} />,
                  },
                ]}
                filas={g.pedidos}
                claveDe={(p) => p.id}
                onFila={(p) =>
                  router.push({ pathname: '/(admin)/pedidos', params: { id: p.id, fecha } })
                }
              />
            </Seccion>
          ))}
        </>
      ) : null}
    </Pantalla>
  );
}

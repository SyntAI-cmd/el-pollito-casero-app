import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Pressable, View, useWindowDimensions } from 'react-native';

import { Chips, Seccion, Tabla } from '@/components/admin/controles';
import { Boton } from '@/components/ui/Boton';
import { Campo } from '@/components/ui/Campo';
import { Badge } from '@/components/ui/Estado';
import { ErrorCarga, Pantalla } from '@/components/ui/Pantalla';
import { MetricaHero, Tarjeta } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver, mensajeDeError, type Esquemas } from '@/lib/api';
import { usePreciosCliente, useUsuarios } from '@/lib/consultas';
import { horaCorta, pesos } from '@/lib/formato';
import { tokens } from '@/theme/tokens';

type Linea = Esquemas['LineaExtracto'];
const TIPO_LINEA: Record<string, string> = {
  cargo: 'Pedido',
  ajuste_peso: 'Balanza',
  anulacion: 'Anulación',
  pago: 'Pago',
  reintegro: 'Reintegro',
  ajuste_manual: 'Ajuste',
};

export default function FichaCliente() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const queryClient = useQueryClient();
  const { width } = useWindowDimensions();
  const [edicion, setEdicion] = useState<Record<string, string>>({});
  const [precios, setPrecios] = useState<Record<string, string>>({});
  const [envases, setEnvases] = useState({ dejados: '', devueltos: '' });
  const [ajuste, setAjuste] = useState({ importe: '', motivo: '' });

  const cliente = useQuery({
    queryKey: ['cliente', id],
    queryFn: async () =>
      desenvolver(
        await api.GET('/clientes/{cliente_id}', { params: { path: { cliente_id: id } } }),
      ),
  });
  const extracto = useQuery({
    queryKey: ['extracto', id],
    queryFn: async () =>
      desenvolver(
        await api.GET('/clientes/{cliente_id}/extracto', { params: { path: { cliente_id: id } } }),
      ),
  });
  const preciosResueltos = usePreciosCliente(id);
  const usuarios = useUsuarios();
  const preventistas = (usuarios.data ?? []).filter((u) => u.rol === 'preventista' && u.activo);
  const cobradores = (usuarios.data ?? []).filter((u) => u.rol === 'cobrador' && u.activo);

  const invalidar = () => {
    queryClient.invalidateQueries({ queryKey: ['cliente', id] });
    queryClient.invalidateQueries({ queryKey: ['extracto', id] });
    queryClient.invalidateQueries({ queryKey: ['cliente', id, 'precios'] });
    queryClient.invalidateQueries({ queryKey: ['clientes'] });
  };
  const guardarFicha = useMutation({
    mutationFn: async (cambios: Record<string, unknown>) =>
      desenvolver(
        await api.PATCH('/clientes/{cliente_id}', {
          params: { path: { cliente_id: id } },
          body: cambios,
        }),
      ),
    onSuccess: () => {
      setEdicion({});
      invalidar();
    },
  });
  const guardarPrecios = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.PUT('/clientes/{cliente_id}/precios', {
          params: { path: { cliente_id: id } },
          body: {
            precios: Object.entries(precios).map(([producto_codigo, v]) => ({
              producto_codigo,
              precio: v.trim() ? v.replace(',', '.') : null,
            })),
          },
        }),
      ),
    onSuccess: () => {
      setPrecios({});
      invalidar();
    },
  });
  const registrarEnvases = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.POST('/clientes/{cliente_id}/envases', {
          params: { path: { cliente_id: id } },
          body: {
            dejados: Number(envases.dejados || 0),
            devueltos: Number(envases.devueltos || 0),
            nota: 'Desde la ficha',
          },
        }),
      ),
    onSuccess: () => {
      setEnvases({ dejados: '', devueltos: '' });
      invalidar();
    },
  });
  const ajustar = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.POST('/clientes/{cliente_id}/ajustes', {
          params: { path: { cliente_id: id } },
          body: { importe: ajuste.importe.replace(',', '.'), motivo: ajuste.motivo },
        }),
      ),
    onSuccess: () => {
      setAjuste({ importe: '', motivo: '' });
      invalidar();
    },
  });

  const c = cliente.data;
  if (cliente.isError && !c) {
    return (
      <Pantalla sinNav>
        <ErrorCarga error={cliente.error} onReintentar={() => cliente.refetch()} />
      </Pantalla>
    );
  }
  if (!c) return <Pantalla sinNav>{null}</Pantalla>;
  const valor = (campo: keyof typeof c) => edicion[campo] ?? String(c[campo] ?? '');
  const hayCambios = Object.keys(edicion).length > 0;
  const ancho = width >= 1024;

  const ficha = (
    <Tarjeta elevada>
      <View className="flex-row items-center justify-between">
        <Texto variante="headline-md">Ficha</Texto>
        <Badge estado={c.activo ? 'entregado' : 'cancelado'} texto={c.activo ? 'Activo' : 'Baja'} />
      </View>
      <View className="mt-2 gap-2">
        {(
          [
            ['nombre_comercial', 'Nombre comercial'],
            ['razon_social', 'Razón social'],
            ['codigo', 'Código'],
            ['cuit', 'CUIT'],
            ['telefono', 'Teléfono'],
            ['direccion', 'Dirección'],
            ['localidad', 'Localidad'],
            ['observaciones', 'Observaciones'],
          ] as const
        ).map(([campo, etiqueta]) => (
          <Campo
            key={campo}
            etiqueta={etiqueta}
            value={valor(campo)}
            onChangeText={(v) => setEdicion((e) => ({ ...e, [campo]: v }))}
          />
        ))}
        <Texto variante="label-md" tono="suave">
          Lista
        </Texto>
        <Chips
          opciones={[
            { valor: 'mayorista', etiqueta: 'Mayorista' },
            { valor: 'intermedio', etiqueta: 'Intermedio' },
            { valor: 'minorista', etiqueta: 'Minorista' },
          ]}
          valor={(edicion.lista as typeof c.lista) ?? c.lista}
          onCambio={(v) => v && setEdicion((e) => ({ ...e, lista: v }))}
          permitirNinguno={false}
        />
        <Texto variante="label-md" tono="suave">
          Turno
        </Texto>
        <Chips
          opciones={[
            { valor: 'manana', etiqueta: 'Mañana' },
            { valor: 'tarde', etiqueta: 'Tarde' },
          ]}
          valor={(edicion.turno as typeof c.turno) ?? c.turno}
          onCambio={(v) => v && setEdicion((e) => ({ ...e, turno: v }))}
          permitirNinguno={false}
        />
        <Texto variante="label-md" tono="suave">
          Preventista
        </Texto>
        <Chips
          opciones={preventistas.map((u) => ({ valor: u.id, etiqueta: u.nombre }))}
          valor={edicion.preventista_id ?? c.preventista_id}
          onCambio={(v) => setEdicion((e) => ({ ...e, preventista_id: v ?? '' }))}
        />
        <Texto variante="label-md" tono="suave">
          Cobrador
        </Texto>
        <Chips
          opciones={cobradores.map((u) => ({ valor: u.id, etiqueta: u.nombre }))}
          valor={edicion.cobrador_id ?? c.cobrador_id}
          onCambio={(v) => setEdicion((e) => ({ ...e, cobrador_id: v ?? '' }))}
        />
        <Pressable
          accessibilityRole="checkbox"
          accessibilityState={{
            checked: (edicion.credito_habilitado ?? String(c.credito_habilitado)) === 'true',
          }}
          onPress={() =>
            setEdicion((e) => ({
              ...e,
              credito_habilitado: String(
                !((e.credito_habilitado ?? String(c.credito_habilitado)) === 'true'),
              ),
            }))
          }
          className="min-h-[48px] flex-row items-center gap-2">
          <MaterialCommunityIcons
            name={
              (edicion.credito_habilitado ?? String(c.credito_habilitado)) === 'true'
                ? 'checkbox-marked'
                : 'checkbox-blank-outline'
            }
            size={24}
            color={tokens.colors.primary}
          />
          <Texto variante="body-lg">Cuenta corriente habilitada</Texto>
        </Pressable>
        <View className="flex-row gap-2">
          <View className="flex-1">
            <Boton
              texto="Guardar ficha"
              icono="content-save"
              onPress={() =>
                guardarFicha.mutate(
                  Object.fromEntries(
                    Object.entries(edicion).map(([k, v]) => [
                      k,
                      k === 'credito_habilitado'
                        ? v === 'true'
                        : k.endsWith('_id') && !v
                          ? null
                          : v,
                    ]),
                  ),
                )
              }
              disabled={!hayCambios}
              cargando={guardarFicha.isPending}
            />
          </View>
          <Boton
            texto={c.activo ? 'Dar de baja' : 'Reactivar'}
            variante="ghost"
            compacto
            onPress={() => guardarFicha.mutate({ activo: !c.activo })}
          />
        </View>
        {guardarFicha.isError ? (
          <Texto variante="body-md" tono="peligro">
            {mensajeDeError(guardarFicha.error)}
          </Texto>
        ) : null}
      </View>
    </Tarjeta>
  );

  const cuenta = (
    <View className="gap-3">
      <MetricaHero
        etiqueta="Cuenta corriente"
        valor={extracto.data ? pesos(extracto.data.saldo) : '—'}
        detalle={
          extracto.data
            ? `${extracto.data.pedidos_pendientes} pedidos sin pagar · saldo a favor ${pesos(extracto.data.saldo_a_favor)} · ${extracto.data.envases} cajones adeudados`
            : ''
        }
        chip={
          extracto.data ? (
            <Badge
              estado={Number(extracto.data.saldo) > 0 ? 'deuda' : 'cobrado'}
              texto={Number(extracto.data.saldo) > 0 ? 'Debe' : 'Al día'}
            />
          ) : null
        }
      />
      <Tarjeta>
        <Texto variante="headline-md">Precios propios</Texto>
        <Texto variante="body-md" tono="suave">
          Pisan la lista {c.lista} · {c.turno}. Vacío = usa la lista; borrá el número para volver a
          la lista.
        </Texto>
        {(preciosResueltos.data ?? []).map((p) => (
          <View
            key={p.producto_codigo}
            className="mt-2 flex-row items-center gap-2 border-t border-border pt-2">
            <View className="flex-1">
              <Texto variante="body-lg">{p.producto_nombre}</Texto>
              <Texto variante="label-caps" tono={p.origen === 'sin_precio' ? 'peligro' : 'suave'}>
                {p.origen === 'propio'
                  ? 'Propio'
                  : p.origen === 'lista'
                    ? 'De lista'
                    : 'Sin precio'}
              </Texto>
            </View>
            <View className="w-[150px]">
              <Campo
                etiqueta="$/kg"
                metrica
                value={
                  precios[p.producto_codigo] ?? (p.origen === 'propio' ? (p.precio ?? '') : '')
                }
                onChangeText={(v) => setPrecios((x) => ({ ...x, [p.producto_codigo]: v }))}
                placeholder={p.origen === 'lista' ? `lista ${p.precio}` : '—'}
              />
            </View>
          </View>
        ))}
        <View className="mt-3">
          <Boton
            texto="Guardar precios"
            icono="tag-check"
            variante="secundario"
            onPress={() => guardarPrecios.mutate()}
            disabled={Object.keys(precios).length === 0}
            cargando={guardarPrecios.isPending}
          />
        </View>
        {guardarPrecios.isError ? (
          <Texto variante="body-md" tono="peligro">
            {mensajeDeError(guardarPrecios.error)}
          </Texto>
        ) : null}
      </Tarjeta>
      <Tarjeta>
        <Texto variante="headline-md">Envases</Texto>
        <View className="mt-2 flex-row gap-2">
          <View className="flex-1">
            <Campo
              etiqueta="Dejados"
              metrica
              value={envases.dejados}
              onChangeText={(v) => setEnvases({ ...envases, dejados: v.replace(/\D/g, '') })}
              placeholder="0"
            />
          </View>
          <View className="flex-1">
            <Campo
              etiqueta="Devueltos"
              metrica
              value={envases.devueltos}
              onChangeText={(v) => setEnvases({ ...envases, devueltos: v.replace(/\D/g, '') })}
              placeholder="0"
            />
          </View>
        </View>
        <View className="mt-2">
          <Boton
            texto="Registrar movimiento"
            icono="package-variant"
            variante="secundario"
            onPress={() => registrarEnvases.mutate()}
            disabled={!Number(envases.dejados) && !Number(envases.devueltos)}
            cargando={registrarEnvases.isPending}
          />
        </View>
      </Tarjeta>
      <Tarjeta>
        <Texto variante="headline-md">Ajuste manual de saldo</Texto>
        <Texto variante="body-md" tono="suave">
          Positivo suma deuda, negativo suma crédito. Queda en el extracto con tu nombre.
        </Texto>
        <View className="mt-2 gap-2">
          <Campo
            etiqueta="Importe"
            metrica
            value={ajuste.importe}
            onChangeText={(v) => setAjuste({ ...ajuste, importe: v })}
            placeholder="-1000"
          />
          <Campo
            etiqueta="Motivo"
            value={ajuste.motivo}
            onChangeText={(v) => setAjuste({ ...ajuste, motivo: v })}
            placeholder="Saldo inicial, arreglo…"
          />
          <Boton
            texto="Aplicar ajuste"
            variante="ghost"
            onPress={() => ajustar.mutate()}
            disabled={!ajuste.importe.trim() || ajuste.motivo.trim().length < 3}
            cargando={ajustar.isPending}
          />
          {ajustar.isError ? (
            <Texto variante="body-md" tono="peligro">
              {mensajeDeError(ajustar.error)}
            </Texto>
          ) : null}
        </View>
      </Tarjeta>
      <Seccion titulo="Extracto" detalle="Reconstruido desde pedidos, pagos y ajustes">
        <Tabla<Linea>
          columnas={[
            {
              clave: 'fecha',
              titulo: 'Fecha',
              ancho: 130,
              render: (l) => (
                <Texto variante="body-md">
                  {l.fecha.slice(0, 10)} {horaCorta(l.fecha)}
                </Texto>
              ),
            },
            {
              clave: 'tipo',
              titulo: 'Tipo',
              ancho: 110,
              render: (l) => <Texto variante="body-md">{TIPO_LINEA[l.tipo] ?? l.tipo}</Texto>,
            },
            {
              clave: 'ref',
              titulo: 'Ref.',
              ancho: 120,
              render: (l) => (
                <Texto variante="body-metric" numberOfLines={1}>
                  {l.referencia}
                </Texto>
              ),
            },
            {
              clave: 'detalle',
              titulo: 'Detalle',
              ancho: 200,
              render: (l) => (
                <Texto variante="body-md" numberOfLines={1}>
                  {l.detalle}
                </Texto>
              ),
            },
            {
              clave: 'importe',
              titulo: 'Importe',
              ancho: 120,
              alinear: 'derecha',
              render: (l) => (
                <Texto variante="body-metric" tono={Number(l.importe) < 0 ? 'exito' : 'normal'}>
                  {pesos(l.importe)}
                </Texto>
              ),
            },
            {
              clave: 'saldo',
              titulo: 'Saldo',
              ancho: 120,
              alinear: 'derecha',
              render: (l) => <Texto variante="body-metric">{pesos(l.saldo)}</Texto>,
            },
          ]}
          filas={[...(extracto.data?.lineas ?? [])].reverse()}
          claveDe={(l) => `${l.fecha}-${l.referencia}-${l.tipo}`}
        />
      </Seccion>
    </View>
  );

  return (
    <Pantalla
      sinNav
      refrescando={cliente.isFetching}
      onRefrescar={() => {
        cliente.refetch();
        extracto.refetch();
      }}>
      <View>
        <Texto variante="label-caps" tono="suave">
          Cliente {c.codigo ?? ''}
        </Texto>
        <Texto variante="headline-lg">{c.nombre_comercial}</Texto>
      </View>
      {ancho ? (
        <View className="flex-row gap-6">
          <View className="flex-[5]">{ficha}</View>
          <View className="flex-[7]">{cuenta}</View>
        </View>
      ) : (
        <>
          {ficha}
          {cuenta}
        </>
      )}
    </Pantalla>
  );
}

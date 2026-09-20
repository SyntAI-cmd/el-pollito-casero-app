import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Stack, useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { Boton } from '@/components/ui/Boton';
import { Campo } from '@/components/ui/Campo';
import { Badge } from '@/components/ui/Estado';
import { Pantalla, Vacio } from '@/components/ui/Pantalla';
import { Tarjeta } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver, mensajeDeError, type Cliente } from '@/lib/api';
import { useClientes, usePreciosCliente, useProductos } from '@/lib/consultas';
import { hoyIso, pesos } from '@/lib/formato';
import { tokens } from '@/theme/tokens';

interface Renglon {
  cajas: string;
  kg: string;
  precio: string; // vacío = usa el resuelto
  guardar: boolean;
}

export default function NuevoPedido() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [busqueda, setBusqueda] = useState('');
  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [turno, setTurno] = useState<'manana' | 'tarde'>('manana');
  const [aCuenta, setACuenta] = useState(false);
  const [observaciones, setObservaciones] = useState('');
  const [renglones, setRenglones] = useState<Record<string, Renglon>>({});
  const [editandoPrecio, setEditandoPrecio] = useState<string | null>(null);

  const clientes = useClientes(busqueda.trim());
  const productos = useProductos();
  const precios = usePreciosCliente(cliente?.id ?? null);
  const precioDe = (codigo: string) => precios.data?.find((p) => p.producto_codigo === codigo);

  const renglon = (codigo: string): Renglon =>
    renglones[codigo] ?? { cajas: '', kg: '', precio: '', guardar: false };
  const cambiar = (codigo: string, cambios: Partial<Renglon>) =>
    setRenglones((r) => ({ ...r, [codigo]: { ...renglon(codigo), ...cambios } }));

  const items = Object.entries(renglones)
    .filter(([, r]) => Number(r.cajas) > 0 || Number(r.kg.replace(',', '.')) > 0)
    .map(([codigo, r]) => ({
      producto_codigo: codigo,
      cajas: Number(r.cajas) > 0 ? Number(r.cajas) : null,
      kg: Number(r.kg.replace(',', '.')) > 0 ? r.kg.replace(',', '.') : null,
      precio: r.precio.trim() ? r.precio.replace(',', '.') : null,
      guardar_precio_propio: r.guardar && !!r.precio.trim(),
    }));
  const sinPrecio = items.filter((i) => !i.precio && !precioDe(i.producto_codigo)?.precio);

  const crear = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.POST('/pedidos', {
          body: {
            cliente_id: cliente!.id,
            fecha_reparto: hoyIso(),
            turno,
            a_cuenta: aCuenta,
            observaciones,
            items,
          },
        }),
      ),
    onSuccess: (pedido) => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
      queryClient.invalidateQueries({ queryKey: ['nota'] });
      router.replace({ pathname: '/(reparto)/entrega/[id]', params: { id: pedido.id } });
    },
  });

  return (
    <>
      <Stack.Screen options={{ title: 'Cargar pedido' }} />
      <Pantalla sinNav>
        {!cliente ? (
          <>
            <Campo
              etiqueta="Cliente"
              value={busqueda}
              onChangeText={setBusqueda}
              placeholder="Nombre, CUIT o teléfono"
              autoFocus
            />
            {clientes.data && clientes.data.length === 0 ? (
              <Vacio
                icono="account-search"
                titulo="Sin resultados"
                detalle="Probá con el apodo del comercio o pedí a administración que lo dé de alta."
              />
            ) : null}
            {(clientes.data ?? []).slice(0, 20).map((c) => (
              <Pressable key={c.id} accessibilityRole="button" onPress={() => setCliente(c)}>
                <Tarjeta>
                  <View className="flex-row items-center justify-between gap-2">
                    <View className="flex-1">
                      <Texto variante="headline-md" numberOfLines={1}>
                        {c.nombre_comercial}
                      </Texto>
                      <Texto variante="body-md" tono="suave" numberOfLines={1}>
                        {c.direccion || c.razon_social}
                      </Texto>
                    </View>
                    {!c.credito_habilitado ? (
                      <Badge estado="pendiente" texto="Sin cta. cte." />
                    ) : null}
                    <MaterialCommunityIcons
                      name="chevron-right"
                      size={24}
                      color={tokens.colors.pending}
                    />
                  </View>
                </Tarjeta>
              </Pressable>
            ))}
          </>
        ) : (
          <>
            <Tarjeta elevada>
              <View className="flex-row items-center justify-between">
                <View className="flex-1">
                  <Texto variante="label-caps" tono="suave">
                    Cliente
                  </Texto>
                  <Texto variante="headline-md">{cliente.nombre_comercial}</Texto>
                </View>
                <Boton
                  texto="Cambiar"
                  variante="ghost"
                  compacto
                  onPress={() => {
                    setCliente(null);
                    setRenglones({});
                  }}
                />
              </View>
              <View className="mt-3 flex-row gap-2" accessibilityRole="radiogroup">
                {(
                  [
                    ['manana', 'Mañana'],
                    ['tarde', 'Tarde'],
                  ] as const
                ).map(([valor, etiqueta]) => (
                  <Pressable
                    key={valor}
                    accessibilityRole="radio"
                    accessibilityState={{ checked: turno === valor }}
                    onPress={() => setTurno(valor)}
                    className={`h-12 flex-1 items-center justify-center rounded-pill ${turno === valor ? 'bg-charcoal' : 'border border-border bg-surface'}`}>
                    <Texto variante="label-md" tono={turno === valor ? 'claro' : 'normal'}>
                      {etiqueta}
                    </Texto>
                  </Pressable>
                ))}
              </View>
              <Pressable
                accessibilityRole="checkbox"
                accessibilityState={{ checked: aCuenta, disabled: !cliente.credito_habilitado }}
                disabled={!cliente.credito_habilitado}
                onPress={() => setACuenta((v) => !v)}
                className="mt-3 min-h-[48px] flex-row items-center gap-2">
                <MaterialCommunityIcons
                  name={aCuenta ? 'checkbox-marked' : 'checkbox-blank-outline'}
                  size={24}
                  color={cliente.credito_habilitado ? tokens.colors.primary : tokens.colors.pending}
                />
                <Texto variante="body-lg" tono={cliente.credito_habilitado ? 'normal' : 'suave'}>
                  A cuenta corriente{cliente.credito_habilitado ? '' : ' (no habilitada)'}
                </Texto>
              </Pressable>
            </Tarjeta>

            <Texto variante="headline-md">Productos</Texto>
            {(productos.data ?? []).map((prod) => {
              const r = renglon(prod.codigo);
              const resuelto = precioDe(prod.codigo);
              const precioMostrado = r.precio.trim()
                ? pesos(r.precio.replace(',', '.'))
                : resuelto?.precio
                  ? pesos(resuelto.precio)
                  : null;
              return (
                <Tarjeta key={prod.codigo}>
                  <View className="flex-row items-center justify-between">
                    <Texto variante="headline-md">{prod.nombre}</Texto>
                    <Pressable
                      accessibilityRole="button"
                      accessibilityLabel={`Precio por kilo de ${prod.nombre}: ${precioMostrado ?? 'sin precio'}. Editar`}
                      onPress={() =>
                        setEditandoPrecio(editandoPrecio === prod.codigo ? null : prod.codigo)
                      }
                      className="min-h-[48px] flex-row items-center gap-1 rounded-pill px-2">
                      {precioMostrado ? (
                        <Texto
                          variante="body-metric"
                          tono={r.precio.trim() ? 'primario' : 'normal'}>
                          {precioMostrado}/kg
                        </Texto>
                      ) : (
                        <Badge estado="sin_precio" texto="Sin precio" />
                      )}
                      <MaterialCommunityIcons
                        name="pencil"
                        size={18}
                        color={tokens.colors.primary}
                      />
                    </Pressable>
                  </View>
                  {resuelto?.origen === 'propio' && !r.precio.trim() ? (
                    <Texto variante="label-caps" tono="suave">
                      Precio propio del cliente
                    </Texto>
                  ) : null}
                  {editandoPrecio === prod.codigo ? (
                    <View className="mt-2 gap-2">
                      <Campo
                        etiqueta="Precio por kilo"
                        metrica
                        value={r.precio}
                        onChangeText={(precio) => cambiar(prod.codigo, { precio })}
                        placeholder={resuelto?.precio ?? '0'}
                      />
                      <Pressable
                        accessibilityRole="checkbox"
                        accessibilityState={{ checked: r.guardar }}
                        onPress={() => cambiar(prod.codigo, { guardar: !r.guardar })}
                        className="min-h-[48px] flex-row items-center gap-2">
                        <MaterialCommunityIcons
                          name={r.guardar ? 'checkbox-marked' : 'checkbox-blank-outline'}
                          size={24}
                          color={tokens.colors.primary}
                        />
                        <Texto variante="body-md">Guardar como precio propio del cliente</Texto>
                      </Pressable>
                    </View>
                  ) : null}
                  <View className="mt-2 flex-row gap-2">
                    <View className="flex-1">
                      <Campo
                        etiqueta="Cajas"
                        metrica
                        value={r.cajas}
                        onChangeText={(cajas) =>
                          cambiar(prod.codigo, { cajas: cajas.replace(/[^0-9]/g, '') })
                        }
                        placeholder="0"
                      />
                    </View>
                    <View className="flex-1">
                      <Campo
                        etiqueta="Kilos"
                        metrica
                        value={r.kg}
                        onChangeText={(kg) => cambiar(prod.codigo, { kg })}
                        placeholder="0"
                      />
                    </View>
                  </View>
                </Tarjeta>
              );
            })}

            <Campo
              etiqueta="Observaciones para el remito"
              value={observaciones}
              onChangeText={setObservaciones}
              placeholder="Opcional"
              multiline
            />

            {sinPrecio.length > 0 ? (
              <Texto variante="body-md" tono="peligro">
                {sinPrecio.map((i) => i.producto_codigo).join(', ')} queda sin precio hasta que
                alguien lo tipee. El pedido se puede cargar igual.
              </Texto>
            ) : null}
            <Boton
              texto={`Cargar pedido${items.length ? ` (${items.length})` : ''}`}
              icono="cart-check"
              onPress={() => crear.mutate()}
              disabled={items.length === 0}
              cargando={crear.isPending}
            />
            {crear.isError ? (
              <Texto variante="body-md" tono="peligro">
                {mensajeDeError(crear.error)}
              </Texto>
            ) : null}
          </>
        )}
      </Pantalla>
    </>
  );
}

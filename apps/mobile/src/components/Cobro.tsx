import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Image, Platform, Pressable, View } from 'react-native';

import { Boton } from '@/components/ui/Boton';
import { Campo } from '@/components/ui/Campo';
import { Badge } from '@/components/ui/Estado';
import { Tarjeta } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver, mensajeDeError, type Esquemas } from '@/lib/api';
import { useCola } from '@/lib/cola';
import { subirComprobante, tomarFoto, type Foto } from '@/lib/foto';
import { pesos } from '@/lib/formato';
import { nuevaId } from '@/lib/ids';
import { tokens } from '@/theme/tokens';

type Medio = Esquemas['Medio'];
const MEDIOS: { valor: Medio; etiqueta: string; icono: 'cash' | 'bank-transfer' | 'checkbook' }[] =
  [
    { valor: 'efectivo', etiqueta: 'Efectivo', icono: 'cash' },
    { valor: 'transferencia', etiqueta: 'Transferencia', icono: 'bank-transfer' },
    { valor: 'cheque', etiqueta: 'Cheque', icono: 'checkbook' },
  ];

interface Parte {
  id: string;
  medio: Medio;
  importe: string;
  foto: Foto | null;
  comprobanteId: string | null;
  subiendo: boolean;
  error: string | null;
}

/** Aritmética en centavos enteros: nada de floats con plata. */
function aCentavos(texto: string): number {
  const limpio = texto.replace(/\./g, '').replace(',', '.').trim();
  if (!/^\d+(\.\d{0,2})?$/.test(limpio)) return NaN;
  const [entero, decimales = ''] = limpio.split('.');
  return Number(entero) * 100 + Number(decimales.padEnd(2, '0'));
}
const deCentavos = (c: number): string => (c / 100).toFixed(2);

/**
 * Cobro mixto: varias partes por medio distinto que suman el total. Transferencia y cheque exigen
 * la foto del comprobante. Con `total` fijo (cobro en la entrega) las partes deben sumarlo exacto;
 * sin total (pago a cuenta) el importe es libre.
 */
export function Cobro({
  clienteId,
  pedidoId,
  total,
  onListo,
}: {
  clienteId: string;
  pedidoId: string | null;
  total: string | null;
  onListo: (pago: Esquemas['PagoSalida'] | null) => void;
}) {
  const queryClient = useQueryClient();
  const [idempotencia] = useState(nuevaId);
  const [partes, setPartes] = useState<Parte[]>([
    {
      id: nuevaId(),
      medio: 'efectivo',
      importe: total ?? '',
      foto: null,
      comprobanteId: null,
      subiendo: false,
      error: null,
    },
  ]);
  const [nota, setNota] = useState('');

  const cambiar = (id: string, cambios: Partial<Parte>) =>
    setPartes((ps) => ps.map((p) => (p.id === id ? { ...p, ...cambios } : p)));

  const sumaCentavos = partes.reduce((acc, p) => acc + (aCentavos(p.importe) || 0), 0);
  const totalCentavos = total ? aCentavos(total) : null;
  const faltaFoto = partes.some((p) => p.medio !== 'efectivo' && !p.comprobanteId);
  const importesValidos = partes.every((p) => aCentavos(p.importe) > 0);
  const cuadra = totalCentavos === null || sumaCentavos === totalCentavos;
  const listo = importesValidos && cuadra && !faltaFoto && partes.length > 0;
  const soloEfectivo = partes.every((p) => p.medio === 'efectivo');

  const sacarFoto = async (parte: Parte, deGaleria = false) => {
    try {
      const foto = await tomarFoto(deGaleria);
      if (!foto) return;
      cambiar(parte.id, { foto, subiendo: true, error: null });
      const comprobante = await subirComprobante(foto, 'comprobante', pedidoId);
      cambiar(parte.id, { comprobanteId: comprobante.id, subiendo: false });
    } catch (error) {
      cambiar(parte.id, { subiendo: false, error: mensajeDeError(error) });
    }
  };

  const registrar = useMutation({
    mutationFn: async () => {
      const cuerpo = {
        idempotencia,
        cliente_id: clienteId,
        pedido_id: pedidoId,
        nota,
        partes: partes.map((p) => ({
          medio: p.medio,
          importe: deCentavos(aCentavos(p.importe)),
          comprobante_id: p.comprobanteId,
        })),
      };
      if (soloEfectivo) {
        // Sin fotos no depende de la red: va a la cola y se manda cuando haya señal.
        await useCola.getState().encolar({
          id: idempotencia,
          descripcion: `Cobro ${pesos(deCentavos(sumaCentavos))}`,
          metodo: 'POST',
          ruta: '/pagos',
          cuerpo,
          claveQuery: pedidoId ? ['pedido', pedidoId] : ['cuentas'],
        });
        await useCola.getState().procesar((m) => {
          if (m.claveQuery) queryClient.invalidateQueries({ queryKey: m.claveQuery });
        });
        return null;
      }
      return desenvolver(await api.POST('/pagos', { body: cuerpo }));
    },
    onSuccess: (pago) => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] });
      queryClient.invalidateQueries({ queryKey: ['cuentas'] });
      queryClient.invalidateQueries({ queryKey: ['caja'] });
      if (pedidoId) queryClient.invalidateQueries({ queryKey: ['pedido', pedidoId] });
      onListo(pago);
    },
  });

  return (
    <View className="gap-4">
      {partes.map((parte, i) => (
        <Tarjeta key={parte.id}>
          <View className="flex-row items-center justify-between">
            <Texto variante="label-caps" tono="suave">
              Parte {i + 1}
            </Texto>
            {partes.length > 1 ? (
              <Boton
                texto="Quitar"
                variante="ghost"
                compacto
                onPress={() => setPartes((ps) => ps.filter((p) => p.id !== parte.id))}
              />
            ) : null}
          </View>
          <View className="mt-2 flex-row gap-2" accessibilityRole="radiogroup">
            {MEDIOS.map((m) => {
              const activo = parte.medio === m.valor;
              return (
                <Pressable
                  key={m.valor}
                  accessibilityRole="radio"
                  accessibilityState={{ checked: activo }}
                  onPress={() => cambiar(parte.id, { medio: m.valor })}
                  className={`min-h-[48px] flex-1 flex-row items-center justify-center gap-1 rounded-pill border px-2 ${activo ? 'border-primary bg-primary' : 'border-border bg-surface'}`}>
                  <MaterialCommunityIcons
                    name={m.icono}
                    size={18}
                    color={activo ? '#FFFFFF' : tokens.colors['on-surface']}
                  />
                  <Texto variante="label-md" tono={activo ? 'claro' : 'normal'}>
                    {m.etiqueta}
                  </Texto>
                </Pressable>
              );
            })}
          </View>
          <View className="mt-3">
            <Campo
              etiqueta="Importe"
              metrica
              value={parte.importe}
              onChangeText={(importe) => cambiar(parte.id, { importe })}
              placeholder="0"
            />
          </View>
          {parte.medio !== 'efectivo' ? (
            <View className="mt-3 gap-2">
              {parte.foto ? (
                <View className="flex-row items-center gap-3">
                  <Image
                    source={{ uri: parte.foto.uri }}
                    style={{ width: 72, height: 72, borderRadius: 12 }}
                    accessibilityLabel="Foto del comprobante"
                  />
                  <View className="flex-1">
                    {parte.subiendo ? (
                      <Badge estado="pendiente" texto="Subiendo…" />
                    ) : parte.comprobanteId ? (
                      <Badge estado="cobrado" texto="Comprobante subido" />
                    ) : (
                      <Badge estado="deuda" texto="No se subió" />
                    )}
                    {parte.error ? (
                      <Texto variante="body-md" tono="peligro">
                        {parte.error}
                      </Texto>
                    ) : null}
                  </View>
                </View>
              ) : (
                <Texto variante="body-md" tono="peligro">
                  {parte.medio === 'cheque' ? 'El cheque' : 'La transferencia'} necesita la foto del
                  comprobante.
                </Texto>
              )}
              <View className="flex-row gap-2">
                <View className="flex-1">
                  <Boton
                    texto={parte.foto ? 'Otra foto' : 'Sacar foto'}
                    icono="camera"
                    variante="secundario"
                    onPress={() => sacarFoto(parte)}
                    disabled={parte.subiendo}
                  />
                </View>
                {Platform.OS !== 'web' ? (
                  <Boton
                    texto="Galería"
                    icono="image"
                    variante="ghost"
                    compacto
                    onPress={() => sacarFoto(parte, true)}
                    disabled={parte.subiendo}
                  />
                ) : null}
              </View>
            </View>
          ) : null}
        </Tarjeta>
      ))}

      <Boton
        texto="Agregar otra parte"
        icono="plus"
        variante="ghost"
        onPress={() =>
          setPartes((ps) => [
            ...ps,
            {
              id: nuevaId(),
              medio: 'transferencia',
              importe:
                totalCentavos !== null && sumaCentavos < totalCentavos
                  ? deCentavos(totalCentavos - sumaCentavos)
                  : '',
              foto: null,
              comprobanteId: null,
              subiendo: false,
              error: null,
            },
          ])
        }
        disabled={partes.length >= 6}
      />

      <Tarjeta elevada>
        <View className="flex-row items-center justify-between">
          <Texto variante="label-caps" tono="suave">
            Suma de las partes
          </Texto>
          <Texto variante="headline-md" tono={cuadra ? 'exito' : 'peligro'}>
            {pesos(deCentavos(sumaCentavos))}
          </Texto>
        </View>
        {totalCentavos !== null ? (
          <Texto variante="body-md" tono={cuadra ? 'suave' : 'peligro'}>
            {cuadra
              ? 'Cuadra con el total a cobrar.'
              : `Tiene que sumar ${pesos(total)}: ${sumaCentavos < totalCentavos ? 'faltan' : 'sobran'} ${pesos(deCentavos(Math.abs(totalCentavos - sumaCentavos)))}.`}
          </Texto>
        ) : null}
        <View className="mt-3">
          <Campo etiqueta="Nota" value={nota} onChangeText={setNota} placeholder="Opcional" />
        </View>
        <View className="mt-4">
          <Boton
            texto={soloEfectivo ? 'Registrar cobro' : 'Registrar cobro con comprobante'}
            icono="cash-check"
            onPress={() => registrar.mutate()}
            disabled={!listo}
            cargando={registrar.isPending}
          />
        </View>
        {registrar.isError ? (
          <Texto variante="body-md" tono="peligro" className="mt-2">
            {mensajeDeError(registrar.error)}
          </Texto>
        ) : null}
      </Tarjeta>
    </View>
  );
}

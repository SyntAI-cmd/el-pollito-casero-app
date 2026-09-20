import { MaterialCommunityIcons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { View } from 'react-native';

import { Texto } from '@/components/ui/Texto';
import type { EstadoPedido } from '@/lib/api';
import { ETIQUETA_ESTADO } from '@/lib/formato';
import { tokens } from '@/theme/tokens';

type Icono = ComponentProps<typeof MaterialCommunityIcons>['name'];

/**
 * Nunca un estado solo con color: color + ícono + texto explícito.
 */
const ESTILO: Record<string, { fondo: string; texto: string; color: string; icono: Icono }> = {
  recibido: {
    fondo: 'bg-border',
    texto: 'text-on-surface-v',
    color: tokens.colors.pending,
    icono: 'inbox-arrow-down',
  },
  preparando: {
    fondo: 'bg-border',
    texto: 'text-on-surface-v',
    color: tokens.colors.pending,
    icono: 'scale',
  },
  en_camino: {
    fondo: 'bg-primary/10',
    texto: 'text-primary',
    color: tokens.colors.primary,
    icono: 'truck-fast',
  },
  entregado: {
    fondo: 'bg-success/10',
    texto: 'text-success',
    color: tokens.colors.success,
    icono: 'check-circle',
  },
  cancelado: {
    fondo: 'bg-danger/10',
    texto: 'text-danger',
    color: tokens.colors.danger,
    icono: 'close-circle',
  },
  deuda: {
    fondo: 'bg-danger/10',
    texto: 'text-danger',
    color: tokens.colors.danger,
    icono: 'alert-circle',
  },
  pendiente: {
    fondo: 'bg-border',
    texto: 'text-on-surface-v',
    color: tokens.colors.pending,
    icono: 'clock-outline',
  },
  cobrado: {
    fondo: 'bg-success/10',
    texto: 'text-success',
    color: tokens.colors.success,
    icono: 'cash-check',
  },
  sin_precio: {
    fondo: 'bg-danger/10',
    texto: 'text-danger',
    color: tokens.colors.danger,
    icono: 'tag-off',
  },
};

export function Badge({
  estado,
  texto,
}: {
  estado: EstadoPedido | keyof typeof ESTILO;
  texto?: string;
}) {
  const estilo = ESTILO[estado] ?? ESTILO.pendiente;
  const etiqueta = texto ?? ETIQUETA_ESTADO[estado] ?? estado;
  return (
    <View
      className={`flex-row items-center gap-1 rounded-pill px-2.5 py-1 ${estilo.fondo}`}
      accessibilityLabel={`Estado: ${etiqueta}`}>
      <MaterialCommunityIcons name={estilo.icono} size={14} color={estilo.color} />
      <Texto variante="label-caps" className={estilo.texto}>
        {etiqueta}
      </Texto>
    </View>
  );
}

const PASOS = ['Cargado', 'Pesado', 'En reparto', 'Entregado'] as const;

function pasoDe(estado: EstadoPedido, pesado: boolean): number {
  if (estado === 'entregado') return 3;
  if (estado === 'en_camino') return 2;
  if (pesado || estado === 'preparando') return 1;
  return 0;
}

/**
 * Stepper de 4 puntos. Riel de 3px; completos en verde con check, el activo naranja con halo,
 * pendientes en gris. Etiquetas en label-caps debajo.
 */
export function Stepper({ estado, pesado }: { estado: EstadoPedido; pesado: boolean }) {
  const activo = pasoDe(estado, pesado);
  const cancelado = estado === 'cancelado';
  return (
    <View
      className="flex-row items-start"
      accessibilityRole="progressbar"
      accessibilityLabel={
        cancelado ? 'Pedido cancelado' : `Paso ${activo + 1} de 4: ${PASOS[activo]}`
      }>
      {PASOS.map((paso, i) => {
        const completo = !cancelado && i < activo;
        const esActivo = !cancelado && i === activo;
        const colorPunto = completo
          ? tokens.colors.success
          : esActivo
            ? tokens.colors.primary
            : tokens.colors.border;
        const rielColor = completo ? tokens.colors.success : tokens.colors.border;
        return (
          <View key={paso} className="flex-1 items-center">
            <View className="w-full flex-row items-center">
              <View
                className="h-[3px] flex-1"
                style={{ backgroundColor: i === 0 ? 'transparent' : rielColor }}
              />
              <View
                className="h-7 w-7 items-center justify-center rounded-pill"
                style={esActivo ? { backgroundColor: 'rgba(247,70,3,0.2)' } : undefined}>
                <View
                  className="h-5 w-5 items-center justify-center rounded-pill"
                  style={{ backgroundColor: colorPunto }}>
                  {completo ? (
                    <MaterialCommunityIcons name="check" size={14} color="#FFFFFF" />
                  ) : null}
                  {esActivo ? <View className="h-2 w-2 rounded-pill bg-white" /> : null}
                </View>
              </View>
              <View
                className="h-[3px] flex-1"
                style={{
                  backgroundColor:
                    i === PASOS.length - 1
                      ? 'transparent'
                      : completo
                        ? tokens.colors.success
                        : tokens.colors.border,
                }}
              />
            </View>
            <Texto
              variante="label-caps"
              className={`mt-1 text-center ${esActivo ? 'text-primary' : completo ? 'text-on-surface' : 'text-pending'}`}>
              {paso}
            </Texto>
          </View>
        );
      })}
    </View>
  );
}

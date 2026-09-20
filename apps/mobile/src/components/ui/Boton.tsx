import { MaterialCommunityIcons } from '@expo/vector-icons';
import type { ComponentProps } from 'react';
import { ActivityIndicator, Pressable, Text, View, type PressableProps } from 'react-native';

import { tokens } from '@/theme/tokens';

type Icono = ComponentProps<typeof MaterialCommunityIcons>['name'];

interface Props extends Omit<PressableProps, 'children' | 'style'> {
  texto: string;
  variante?: 'primario' | 'secundario' | 'ghost' | 'peligro';
  icono?: Icono;
  cargando?: boolean;
  compacto?: boolean;
  className?: string;
}

const FONDO = {
  primario: 'bg-primary active:bg-primary-press',
  secundario: 'bg-charcoal active:bg-cherry',
  ghost: 'bg-transparent active:bg-primary/10',
  peligro: 'bg-danger active:bg-cherry',
};

const TEXTO = {
  primario: 'text-white',
  secundario: 'text-white',
  ghost: 'text-primary',
  peligro: 'text-white',
};

/** Botón pill de 52px (mínimo táctil 48): el repartidor usa guantes o tiene las manos mojadas. */
export function Boton({
  texto,
  variante = 'primario',
  icono,
  cargando = false,
  compacto = false,
  disabled,
  className = '',
  ...resto
}: Props) {
  const inactivo = disabled || cargando;
  const colorTexto = variante === 'ghost' ? tokens.colors.primary : '#FFFFFF';
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: !!inactivo, busy: cargando }}
      disabled={inactivo}
      className={`min-h-[48px] flex-row items-center justify-center gap-2 rounded-pill px-5 ${
        compacto ? 'h-12' : 'h-[52px] w-full'
      } ${FONDO[variante]} ${inactivo ? 'opacity-50' : ''} ${className}`}
      {...resto}>
      {cargando ? (
        <ActivityIndicator color={colorTexto} />
      ) : icono ? (
        <MaterialCommunityIcons name={icono} size={20} color={colorTexto} />
      ) : null}
      <Text className={`font-bold text-[15px] ${TEXTO[variante]}`}>{texto}</Text>
    </Pressable>
  );
}

/** Botón redondo de ícono solo (llamar, navegar). 48×48 como mínimo. */
export function BotonIcono({
  icono,
  etiqueta,
  variante = 'suave',
  onPress,
  disabled,
}: {
  icono: Icono;
  etiqueta: string;
  variante?: 'suave' | 'oscuro' | 'primario';
  onPress?: () => void;
  disabled?: boolean;
}) {
  const fondo = {
    suave: 'bg-background active:bg-border',
    oscuro: 'bg-charcoal active:bg-cherry',
    primario: 'bg-primary active:bg-primary-press',
  }[variante];
  const color = variante === 'suave' ? tokens.colors['on-surface'] : '#FFFFFF';
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={etiqueta}
      onPress={onPress}
      disabled={disabled}
      className={`h-12 w-12 items-center justify-center rounded-pill ${fondo} ${disabled ? 'opacity-40' : ''}`}>
      <MaterialCommunityIcons name={icono} size={22} color={color} />
    </Pressable>
  );
}

/** FAB de 56×56 con sombra naranja para la acción principal de la pantalla. */
export function Fab({
  icono = 'plus',
  etiqueta,
  onPress,
}: {
  icono?: Icono;
  etiqueta: string;
  onPress: () => void;
}) {
  return (
    <View style={tokens.sombras.fab} className="rounded-pill">
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={etiqueta}
        onPress={onPress}
        className="h-14 w-14 items-center justify-center rounded-pill bg-primary active:bg-primary-press">
        <MaterialCommunityIcons name={icono} size={28} color="#FFFFFF" />
      </Pressable>
    </View>
  );
}

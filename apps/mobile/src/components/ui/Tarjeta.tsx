import { MaterialCommunityIcons } from '@expo/vector-icons';
import type { ComponentProps, ReactNode } from 'react';
import { Pressable, View, type ViewProps } from 'react-native';

import { Texto } from '@/components/ui/Texto';
import { tokens } from '@/theme/tokens';

type Icono = ComponentProps<typeof MaterialCommunityIcons>['name'];

interface Props extends ViewProps {
  children: ReactNode;
  elevada?: boolean;
  className?: string;
}

/** Card: superficie #F9F9F9, radio 20, borde 1px y sombra suave. `elevada` = blanca y héroe. */
export function Tarjeta({ children, elevada = false, className = '', style, ...resto }: Props) {
  return (
    <View
      className={`rounded-card border border-border p-4 ${elevada ? 'bg-surface-white' : 'bg-surface'} ${className}`}
      style={[elevada ? tokens.sombras.hero : tokens.sombras.card, style]}
      {...resto}>
      {children}
    </View>
  );
}

/** Tarjeta oscura de métrica grande para tableros: "1.420 kg", "$ 840.500". */
export function MetricaHero({
  etiqueta,
  valor,
  detalle,
  chip,
  children,
}: {
  etiqueta: string;
  valor: string;
  detalle?: string;
  chip?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <View
      className="overflow-hidden rounded-panel bg-charcoal p-5"
      style={tokens.sombras.hero}
      accessibilityRole="summary">
      <View className="absolute -right-10 -top-10 h-40 w-40 rounded-pill bg-cherry opacity-70" />
      <View className="flex-row items-center justify-between">
        <Texto variante="label-caps" tono="claro-suave">
          {etiqueta}
        </Texto>
        {chip}
      </View>
      <Texto variante="display" tono="claro" className="mt-2">
        {valor}
      </Texto>
      {detalle ? (
        <Texto variante="body-md" tono="claro-suave" className="mt-1">
          {detalle}
        </Texto>
      ) : null}
      {children}
    </View>
  );
}

export interface Acceso {
  icono: Icono;
  titulo: string;
  subtitulo: string;
  contador?: string;
  onPress: () => void;
}

/** Grilla 2×2 de accesos rápidos (tira de 4 en tablet). Ícono monocromo 28px arriba a la izquierda. */
export function GrillaAccesos({ accesos }: { accesos: Acceso[] }) {
  return (
    <View className="flex-row flex-wrap gap-3">
      {accesos.map((acceso) => (
        <Pressable
          key={acceso.titulo}
          accessibilityRole="button"
          accessibilityLabel={`${acceso.titulo}${acceso.contador ? `, ${acceso.contador}` : ''}`}
          onPress={acceso.onPress}
          className="min-h-[120px] w-[47%] grow rounded-card border border-border bg-surface p-4 active:bg-border md:w-[22%]"
          style={tokens.sombras.card}>
          <View className="flex-row items-start justify-between">
            <View className="h-11 w-11 items-center justify-center rounded-pill bg-background">
              <MaterialCommunityIcons
                name={acceso.icono}
                size={28}
                color={tokens.colors['on-surface']}
              />
            </View>
            {acceso.contador ? (
              <View className="rounded-pill bg-cherry px-2.5 py-1">
                <Texto variante="label-caps" tono="claro">
                  {acceso.contador}
                </Texto>
              </View>
            ) : null}
          </View>
          <Texto variante="label-caps" tono="suave" className="mt-3">
            {acceso.subtitulo}
          </Texto>
          <Texto variante="headline-md">{acceso.titulo}</Texto>
        </Pressable>
      ))}
    </View>
  );
}

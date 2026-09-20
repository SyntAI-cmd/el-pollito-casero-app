import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import type { BottomTabBarProps } from 'expo-router/build/react-navigation/bottom-tabs/types';
import type { ComponentProps } from 'react';
import { Pressable, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Fab } from '@/components/ui/Boton';
import { Texto } from '@/components/ui/Texto';
import { tokens } from '@/theme/tokens';

type Icono = ComponentProps<typeof MaterialCommunityIcons>['name'];

export interface ItemNav {
  nombre: string; // nombre de ruta dentro del grupo
  etiqueta: string;
  icono: Icono;
}

/**
 * Nav inferior flotante oscura con FAB central. Cuatro pestañas, 48px táctiles, sombra fuerte.
 * En escritorio (lg) se reemplaza por la barra lateral de administración; acá solo mobile/tablet.
 */
export function NavFlotante({
  props,
  items,
  fab,
}: {
  props: BottomTabBarProps;
  items: ItemNav[];
  fab?: { etiqueta: string; href: string; icono?: Icono };
}) {
  const { state, navigation } = props;
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const activa = state.routes[state.index]?.name;
  const mitad = Math.ceil(items.length / 2);

  const boton = (item: ItemNav) => {
    const esActiva = activa === item.nombre;
    return (
      <Pressable
        key={item.nombre}
        accessibilityRole="tab"
        accessibilityState={{ selected: esActiva }}
        accessibilityLabel={item.etiqueta}
        onPress={() => navigation.navigate(item.nombre)}
        className="min-h-[48px] flex-1 items-center justify-center gap-0.5 py-1">
        <MaterialCommunityIcons
          name={item.icono}
          size={24}
          color={esActiva ? tokens.colors.primary : 'rgba(255,255,255,0.7)'}
        />
        <Texto variante="label-caps" className={esActiva ? 'text-primary' : 'text-white/70'}>
          {item.etiqueta}
        </Texto>
      </Pressable>
    );
  };

  return (
    <View
      pointerEvents="box-none"
      className="absolute inset-x-0 bottom-0 items-center px-4"
      style={{ paddingBottom: Math.max(insets.bottom, 12) }}>
      <View
        className="w-full max-w-[560px] flex-row items-center rounded-panel bg-charcoal px-2"
        style={tokens.sombras.nav}>
        {items.slice(0, mitad).map(boton)}
        {fab ? (
          <View className="-mt-8 px-1">
            <Fab
              etiqueta={fab.etiqueta}
              icono={fab.icono}
              onPress={() => router.push(fab.href as never)}
            />
          </View>
        ) : null}
        {items.slice(mitad).map(boton)}
      </View>
    </View>
  );
}

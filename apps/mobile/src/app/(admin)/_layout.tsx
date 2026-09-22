import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Redirect, Slot, usePathname, useRouter } from 'expo-router';
import type { ComponentProps } from 'react';
import { Pressable, ScrollView, View, useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { CerrarSesion } from '@/components/CerrarSesion';
import { Texto } from '@/components/ui/Texto';
import { useSesion } from '@/stores/sesion';

type Icono = ComponentProps<typeof MaterialCommunityIcons>['name'];

const SECCIONES: { href: string; etiqueta: string; icono: Icono }[] = [
  { href: '/(admin)', etiqueta: 'Nota del día', icono: 'notebook' },
  { href: '/(admin)/pedidos', etiqueta: 'Pedidos', icono: 'clipboard-list' },
  { href: '/(admin)/nuevo-pedido', etiqueta: 'Cargar pedido', icono: 'cart-plus' },
  { href: '/(admin)/clientes', etiqueta: 'Clientes', icono: 'account-group' },
  { href: '/(admin)/precios', etiqueta: 'Listas de precios', icono: 'tag-multiple' },
  { href: '/(reparto)/pesada', etiqueta: 'Balanza', icono: 'scale' },
  { href: '/(reparto)/carga', etiqueta: 'Carga', icono: 'truck-check' },
  { href: '/(admin)/flota', etiqueta: 'Salidas', icono: 'truck' },
  { href: '/(admin)/rendicion', etiqueta: 'Rendición', icono: 'cash-register' },
  { href: '/(admin)/imprimir', etiqueta: 'Imprimir', icono: 'printer' },
  { href: '/(admin)/equipo', etiqueta: 'Equipo', icono: 'account-hard-hat' },
  { href: '/(admin)/sucursales', etiqueta: 'Sucursales', icono: 'store' },
];

const RUTA_DE = (href: string) => href.replace('/(admin)', '').replace('/(reparto)', '') || '/';

/**
 * Administración: barra lateral oscura en escritorio (≥ 1024 px) y tira horizontal en pantallas
 * chicas. El contenido va a 1280 px como máximo, con 32 px de margen en escritorio.
 */
export default function LayoutAdmin() {
  const rol = useSesion((s) => s.usuario?.rol ?? null);
  const { width } = useWindowDimensions();
  const ruta = usePathname();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  if (!rol) return null; // sin sesión manda el layout raíz, para no redirigir de a dos
  if (rol !== 'admin') return <Redirect href="/" />;
  const escritorio = width >= 1024;

  const activa = (href: string) => {
    const objetivo = RUTA_DE(href);
    return objetivo === '/' ? ruta === '/' : ruta.startsWith(objetivo);
  };

  const item = (s: (typeof SECCIONES)[number]) => (
    <Pressable
      key={s.href}
      accessibilityRole="link"
      accessibilityState={{ selected: activa(s.href) }}
      onPress={() => router.push(s.href as never)}
      className={`min-h-[48px] flex-row items-center gap-3 rounded-input px-3 ${activa(s.href) ? 'bg-primary' : 'active:bg-cherry'} ${escritorio ? '' : 'mr-2'}`}>
      <MaterialCommunityIcons name={s.icono} size={22} color="#FFFFFF" />
      <Texto variante="label-md" tono="claro">
        {s.etiqueta}
      </Texto>
    </Pressable>
  );

  return (
    <View className="flex-1 flex-row bg-background" style={{ paddingTop: insets.top }}>
      {escritorio ? (
        <View className="w-[240px] gap-1 bg-charcoal px-3 py-4" accessibilityRole="menu">
          <View className="mb-4 flex-row items-center justify-between px-3">
            <View>
              <Texto variante="label-caps" tono="claro-suave">
                El Pollito Casero
              </Texto>
              <Texto variante="headline-md" tono="claro">
                Administración
              </Texto>
            </View>
            <CerrarSesion />
          </View>
          {SECCIONES.map(item)}
        </View>
      ) : null}
      <View className="flex-1">
        {!escritorio ? (
          <View className="bg-charcoal">
            <View className="flex-row items-center justify-between px-4 pt-2">
              <Texto variante="headline-md" tono="claro">
                Administración
              </Texto>
              <CerrarSesion />
            </View>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerClassName="px-4 py-2">
              {SECCIONES.map(item)}
            </ScrollView>
          </View>
        ) : null}
        <Slot />
      </View>
    </View>
  );
}

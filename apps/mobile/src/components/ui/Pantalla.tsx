import { MaterialCommunityIcons } from '@expo/vector-icons';
import type { ReactNode } from 'react';
import { Pressable, RefreshControl, ScrollView, View } from 'react-native';

import { Texto } from '@/components/ui/Texto';
import { mensajeDeError } from '@/lib/api';
import { useCola } from '@/lib/cola';
import { tokens } from '@/theme/tokens';

/** Scroll con márgenes por ancho (16/24/32) y 96px abajo por la nav flotante y el FAB. */
export function Pantalla({
  children,
  refrescando,
  onRefrescar,
  sinNav = false,
}: {
  children: ReactNode;
  refrescando?: boolean;
  onRefrescar?: () => void;
  sinNav?: boolean;
}) {
  return (
    <ScrollView
      className="flex-1 bg-background"
      keyboardShouldPersistTaps="handled"
      contentContainerClassName={`gap-4 p-gutter md:p-gutter-tablet lg:p-gutter-desktop web:w-full web:max-w-[1280px] web:self-center ${sinNav ? 'pb-8' : 'pb-nav-safe'}`}
      refreshControl={
        onRefrescar ? (
          <RefreshControl
            refreshing={!!refrescando}
            onRefresh={onRefrescar}
            tintColor={tokens.colors.primary}
          />
        ) : undefined
      }>
      <Pendientes />
      {children}
    </ScrollView>
  );
}

/** Indicador visible de cuántas operaciones esperan señal, y las rechazadas por el servidor. */
export function Pendientes() {
  const pendientes = useCola((s) => s.pendientes);
  const descartar = useCola((s) => s.descartar);
  const procesar = useCola((s) => s.procesar);
  const enEspera = pendientes.filter((m) => !m.error);
  const rechazadas = pendientes.filter((m) => m.error);
  if (pendientes.length === 0) return null;
  return (
    <View className="gap-2">
      {enEspera.length > 0 ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`${enEspera.length} operaciones pendientes de enviar. Reintentar.`}
          onPress={() => procesar()}
          className="flex-row items-center gap-2 rounded-input bg-charcoal px-4 py-3">
          <MaterialCommunityIcons name="cloud-upload-outline" size={20} color="#FFFFFF" />
          <Texto variante="label-md" tono="claro" className="flex-1">
            {enEspera.length === 1
              ? '1 operación pendiente de enviar'
              : `${enEspera.length} operaciones pendientes de enviar`}
          </Texto>
          <Texto variante="label-caps" tono="claro-suave">
            Reintentar
          </Texto>
        </Pressable>
      ) : null}
      {rechazadas.map((m) => (
        <View
          key={m.id}
          className="flex-row items-center gap-2 rounded-input bg-danger/10 px-4 py-3">
          <MaterialCommunityIcons name="alert-circle" size={20} color={tokens.colors.danger} />
          <View className="flex-1">
            <Texto variante="label-md" tono="peligro">
              No se pudo: {m.descripcion}
            </Texto>
            <Texto variante="body-md" tono="suave">
              {m.error}
            </Texto>
          </View>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Descartar"
            onPress={() => descartar(m.id)}
            className="h-12 w-12 items-center justify-center">
            <MaterialCommunityIcons name="close" size={22} color={tokens.colors['on-surface-v']} />
          </Pressable>
        </View>
      ))}
    </View>
  );
}

export function Vacio({
  icono,
  titulo,
  detalle,
}: {
  icono: 'inbox' | 'truck' | 'scale' | 'account-search' | 'wifi-off';
  titulo: string;
  detalle?: string;
}) {
  return (
    <View className="items-center gap-2 rounded-card border border-border bg-surface px-6 py-10">
      <MaterialCommunityIcons name={icono} size={40} color={tokens.colors.pending} />
      <Texto variante="headline-md" className="text-center">
        {titulo}
      </Texto>
      {detalle ? (
        <Texto variante="body-md" tono="suave" className="text-center">
          {detalle}
        </Texto>
      ) : null}
    </View>
  );
}

export function ErrorCarga({ error, onReintentar }: { error: unknown; onReintentar?: () => void }) {
  return (
    <Pressable
      onPress={onReintentar}
      className="flex-row items-center gap-2 rounded-input bg-danger/10 px-4 py-3">
      <MaterialCommunityIcons name="wifi-off" size={20} color={tokens.colors.danger} />
      <Texto variante="label-md" tono="peligro" className="flex-1">
        {mensajeDeError(error)}
      </Texto>
      {onReintentar ? (
        <Texto variante="label-caps" tono="peligro">
          Reintentar
        </Texto>
      ) : null}
    </Pressable>
  );
}

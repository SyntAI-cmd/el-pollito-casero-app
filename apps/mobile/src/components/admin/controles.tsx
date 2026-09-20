import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useEffect, type ReactNode } from 'react';
import { Platform, Pressable, ScrollView, View } from 'react-native';

import { BotonIcono } from '@/components/ui/Boton';
import { Texto } from '@/components/ui/Texto';
import { fechaLarga } from '@/lib/formato';
import { tokens } from '@/theme/tokens';

function sumarDias(iso: string, dias: number): string {
  const [a, m, d] = iso.split('-').map(Number);
  const fecha = new Date(a, m - 1, d + dias);
  return `${fecha.getFullYear()}-${String(fecha.getMonth() + 1).padStart(2, '0')}-${String(fecha.getDate()).padStart(2, '0')}`;
}

/** Día anterior / siguiente con la fecha larga en el medio. */
export function SelectorFecha({
  valor,
  onCambio,
}: {
  valor: string;
  onCambio: (iso: string) => void;
}) {
  return (
    <View className="flex-row items-center gap-2">
      <BotonIcono
        icono="chevron-left"
        etiqueta="Día anterior"
        onPress={() => onCambio(sumarDias(valor, -1))}
      />
      <View className="flex-1 items-center">
        <Texto variante="headline-md">{fechaLarga(valor)}</Texto>
        <Texto variante="label-caps" tono="suave">
          {valor}
        </Texto>
      </View>
      <BotonIcono
        icono="chevron-right"
        etiqueta="Día siguiente"
        onPress={() => onCambio(sumarDias(valor, 1))}
      />
    </View>
  );
}

/** Chips de selección única (o múltiple con `multiple`). Mínimo 48 px de alto. */
export function Chips<T extends string>({
  opciones,
  valor,
  onCambio,
  permitirNinguno = true,
}: {
  opciones: { valor: T; etiqueta: string }[];
  valor: T | null;
  onCambio: (valor: T | null) => void;
  permitirNinguno?: boolean;
}) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerClassName="gap-2">
      {opciones.map((o) => {
        const activo = o.valor === valor;
        return (
          <Pressable
            key={o.valor}
            accessibilityRole="radio"
            accessibilityState={{ checked: activo }}
            onPress={() => onCambio(activo && permitirNinguno ? null : o.valor)}
            className={`min-h-[48px] justify-center rounded-pill border px-4 ${activo ? 'border-charcoal bg-charcoal' : 'border-border bg-surface'}`}>
            <Texto variante="label-md" tono={activo ? 'claro' : 'normal'}>
              {o.etiqueta}
            </Texto>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

export interface Columna<T> {
  clave: string;
  titulo: string;
  ancho: number;
  alinear?: 'izquierda' | 'derecha';
  render: (fila: T) => ReactNode;
}

/**
 * Tabla densa con columnas de ancho fijo y scroll horizontal: la vista que usa administración
 * todo el día en la PC. Filas de 44 px, encabezado en label-caps.
 */
export function Tabla<T>({
  columnas,
  filas,
  claveDe,
  onFila,
  seleccionada,
}: {
  columnas: Columna<T>[];
  filas: T[];
  claveDe: (fila: T) => string;
  onFila?: (fila: T) => void;
  seleccionada?: string | null;
}) {
  const anchoTotal = columnas.reduce((a, c) => a + c.ancho, 0);
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator>
      <View
        style={{ minWidth: anchoTotal }}
        className="rounded-card border border-border bg-surface-white">
        <View className="flex-row border-b border-border bg-background" accessibilityRole="header">
          {columnas.map((c) => (
            <View
              key={c.clave}
              style={{ width: c.ancho }}
              className={`px-3 py-2 ${c.alinear === 'derecha' ? 'items-end' : ''}`}>
              <Texto variante="label-caps" tono="suave">
                {c.titulo}
              </Texto>
            </View>
          ))}
        </View>
        {filas.map((fila) => {
          const clave = claveDe(fila);
          const activa = seleccionada === clave;
          return (
            <Pressable
              key={clave}
              accessibilityRole={onFila ? 'button' : undefined}
              onPress={() => onFila?.(fila)}
              disabled={!onFila}
              className={`min-h-[44px] flex-row items-center border-b border-border ${activa ? 'bg-primary/10' : 'active:bg-background'}`}>
              {columnas.map((c) => (
                <View
                  key={c.clave}
                  style={{ width: c.ancho }}
                  className={`px-3 py-1.5 ${c.alinear === 'derecha' ? 'items-end' : ''}`}>
                  {c.render(fila)}
                </View>
              ))}
            </Pressable>
          );
        })}
        {filas.length === 0 ? (
          <View className="items-center py-8">
            <MaterialCommunityIcons name="inbox" size={28} color={tokens.colors.pending} />
            <Texto variante="body-md" tono="suave">
              Sin filas
            </Texto>
          </View>
        ) : null}
      </View>
    </ScrollView>
  );
}

/** Ctrl+Enter confirma en escritorio (solo web). */
export function useCtrlEnter(accion: () => void, habilitado = true) {
  useEffect(() => {
    if (Platform.OS !== 'web' || !habilitado) return;
    const manejar = (evento: KeyboardEvent) => {
      if ((evento.ctrlKey || evento.metaKey) && evento.key === 'Enter') {
        evento.preventDefault();
        accion();
      }
    };
    globalThis.addEventListener?.('keydown', manejar);
    return () => globalThis.removeEventListener?.('keydown', manejar);
  }, [accion, habilitado]);
}

export function Seccion({
  titulo,
  detalle,
  derecha,
  children,
}: {
  titulo: string;
  detalle?: string;
  derecha?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <View className="gap-3">
      <View className="flex-row items-end justify-between gap-2">
        <View className="flex-1">
          <Texto variante="headline-lg">{titulo}</Texto>
          {detalle ? (
            <Texto variante="body-md" tono="suave">
              {detalle}
            </Texto>
          ) : null}
        </View>
        {derecha}
      </View>
      {children}
    </View>
  );
}

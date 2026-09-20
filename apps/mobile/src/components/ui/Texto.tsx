import { Text, type TextProps, type TextStyle } from 'react-native';

/** Números que no bailan al actualizarse: tabulares en kilos, precios, totales y teléfonos. */
export const TABULAR: TextStyle = { fontVariant: ['tabular-nums'] };

type Variante =
  | 'display'
  | 'headline-lg'
  | 'headline-md'
  | 'body-lg'
  | 'body-md'
  | 'body-metric'
  | 'label-caps'
  | 'label-md';

const CLASES: Record<Variante, string> = {
  display:
    'font-extrabold text-[32px] leading-[36px] tracking-[-0.02em] md:text-[44px] md:leading-[48px]',
  'headline-lg': 'font-bold text-[22px] leading-[28px] md:text-[28px] md:leading-[34px]',
  'headline-md': 'font-bold text-[18px] leading-[24px]',
  'body-lg': 'font-sans text-[16px] leading-[24px]',
  'body-md': 'font-sans text-[14px] leading-[20px]',
  'body-metric': 'font-bold text-[15px] leading-[20px]',
  'label-caps': 'font-bold text-[11px] leading-[16px] uppercase tracking-[0.06em]',
  'label-md': 'font-semibold text-[13px] leading-[18px]',
};

const METRICAS: Variante[] = ['display', 'body-metric'];

interface Props extends TextProps {
  variante?: Variante;
  className?: string;
  tono?: 'normal' | 'suave' | 'claro' | 'claro-suave' | 'primario' | 'exito' | 'peligro';
}

const TONOS = {
  normal: 'text-on-surface',
  suave: 'text-on-surface-v',
  claro: 'text-white',
  'claro-suave': 'text-white/70',
  primario: 'text-primary',
  exito: 'text-success',
  peligro: 'text-danger',
};

export function Texto({
  variante = 'body-lg',
  tono = 'normal',
  className = '',
  style,
  ...resto
}: Props) {
  const tabular = METRICAS.includes(variante) ? TABULAR : undefined;
  return (
    <Text
      className={`${CLASES[variante]} ${TONOS[tono]} ${className}`}
      style={[tabular, style]}
      {...resto}
    />
  );
}

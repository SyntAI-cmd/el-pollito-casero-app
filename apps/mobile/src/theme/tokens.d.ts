import type { ViewStyle } from 'react-native';

export interface Tokens {
  colors: Record<
    | 'primary'
    | 'primary-press'
    | 'charcoal'
    | 'cherry'
    | 'background'
    | 'surface'
    | 'surface-white'
    | 'border'
    | 'on-surface'
    | 'on-surface-v'
    | 'success'
    | 'pending'
    | 'danger',
    string
  >;
  sombras: Record<'card' | 'hero' | 'nav' | 'fab', ViewStyle>;
  TOQUE_MINIMO: number;
}

export const tokens: Tokens;

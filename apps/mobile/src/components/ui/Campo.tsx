import { forwardRef } from 'react';
import { TextInput, View, type TextInputProps } from 'react-native';

import { Texto } from '@/components/ui/Texto';
import { tokens } from '@/theme/tokens';

interface Props extends TextInputProps {
  etiqueta: string;
  error?: string | null;
  ayuda?: string;
  metrica?: boolean; // números tabulares, teclado numérico, texto grande
}

/** Input con radio 16px, etiqueta en label-md y área táctil de 52px. */
export const Campo = forwardRef<TextInput, Props>(function Campo(
  { etiqueta, error, ayuda, metrica = false, className = '', style, ...resto },
  ref,
) {
  return (
    <View className="gap-1">
      <Texto variante="label-md" tono="suave">
        {etiqueta}
      </Texto>
      <TextInput
        ref={ref}
        accessibilityLabel={etiqueta}
        placeholderTextColor={tokens.colors.pending}
        keyboardType={metrica ? 'decimal-pad' : resto.keyboardType}
        className={`min-h-[52px] rounded-input border bg-surface-white px-4 text-on-surface ${
          metrica ? 'font-bold text-[22px]' : 'font-sans text-[16px]'
        } ${error ? 'border-danger' : 'border-border'} ${className}`}
        style={[metrica ? { fontVariant: ['tabular-nums'] } : null, style]}
        {...resto}
      />
      {error ? (
        <Texto variante="body-md" tono="peligro">
          {error}
        </Texto>
      ) : ayuda ? (
        <Texto variante="body-md" tono="suave">
          {ayuda}
        </Texto>
      ) : null}
    </View>
  );
});

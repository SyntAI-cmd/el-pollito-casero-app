/** Tokens del sistema de diseño "Molten Orange on Charcoal" (docs/PROMPT.md). No usar colores sueltos. */
const { tokens } = require('./src/theme/tokens');

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    colors: {
      transparent: 'transparent',
      white: '#FFFFFF',
      ...tokens.colors,
    },
    fontFamily: {
      sans: ['Inter_500Medium'],
      medium: ['Inter_500Medium'],
      semibold: ['Inter_600SemiBold'],
      bold: ['Inter_700Bold'],
      extrabold: ['Inter_800ExtraBold'],
    },
    extend: {
      borderRadius: {
        card: '20px',
        panel: '24px',
        input: '16px',
        pill: '9999px',
      },
      spacing: {
        gutter: '16px',
        'gutter-tablet': '24px',
        'gutter-desktop': '32px',
        'nav-safe': '96px',
      },
    },
  },
  plugins: [],
};

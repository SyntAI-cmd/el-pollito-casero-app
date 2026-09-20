// Extiende app.json con lo que depende del entorno. La clave de Maps para Android se lee de
// GOOGLE_MAPS_ANDROID_KEY (restringida a la app por package + SHA-1, así que puede ir en el
// build); sin ella, react-native-maps muestra el mapa en gris en Android.
module.exports = ({ config }) => ({
  ...config,
  android: {
    ...config.android,
    config: {
      ...config.android?.config,
      googleMaps: { apiKey: process.env.GOOGLE_MAPS_ANDROID_KEY ?? '' },
    },
  },
});

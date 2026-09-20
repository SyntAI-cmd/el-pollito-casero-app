import { useMutation } from '@tanstack/react-query';
import { Redirect } from 'expo-router';
import { useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, TextInput, View } from 'react-native';

import { Boton } from '@/components/ui/Boton';
import { Campo } from '@/components/ui/Campo';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver, mensajeDeError } from '@/lib/api';
import { useSesion } from '@/stores/sesion';

export default function Login() {
  const [usuario, setUsuario] = useState('');
  const [clave, setClave] = useState('');
  const claveRef = useRef<TextInput>(null);
  const iniciar = useSesion((s) => s.iniciar);
  const rol = useSesion((s) => s.usuario?.rol ?? null);

  const entrar = useMutation({
    mutationFn: async () =>
      desenvolver(
        await api.POST('/auth/login', {
          body: { usuario: usuario.trim().toLowerCase(), clave },
        }),
      ),
    onSuccess: (tokens) => iniciar(tokens),
  });

  if (rol) return <Redirect href="/" />;

  const listo = usuario.trim().length >= 2 && clave.length >= 4;

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      className="flex-1 bg-charcoal">
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerClassName="flex-grow justify-center p-gutter web:w-full web:max-w-[440px] web:self-center">
        <View className="mb-8">
          <Texto variante="label-caps" tono="claro-suave">
            El Pollito Casero
          </Texto>
          <Texto variante="display" tono="claro">
            Entrar
          </Texto>
          <Texto variante="body-lg" tono="claro-suave" className="mt-2">
            Con el usuario que te dio administración.
          </Texto>
        </View>
        <View className="gap-4 rounded-panel bg-surface-white p-5">
          <Campo
            etiqueta="Usuario"
            value={usuario}
            onChangeText={setUsuario}
            autoCapitalize="none"
            autoCorrect={false}
            autoComplete="username"
            textContentType="username"
            returnKeyType="next"
            onSubmitEditing={() => claveRef.current?.focus()}
            testID="usuario"
          />
          <Campo
            ref={claveRef}
            etiqueta="Clave"
            value={clave}
            onChangeText={setClave}
            secureTextEntry
            autoComplete="current-password"
            textContentType="password"
            returnKeyType="go"
            onSubmitEditing={() => listo && entrar.mutate()}
            error={entrar.isError ? mensajeDeError(entrar.error) : null}
            testID="clave"
          />
          <Boton
            texto="Entrar"
            icono="login"
            onPress={() => entrar.mutate()}
            disabled={!listo}
            cargando={entrar.isPending}
          />
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

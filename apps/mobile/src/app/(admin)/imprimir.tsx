import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Linking, Platform, View } from 'react-native';

import { Chips, Seccion, SelectorFecha, Tabla } from '@/components/admin/controles';
import { Boton } from '@/components/ui/Boton';
import { Badge } from '@/components/ui/Estado';
import { ErrorCarga, Pantalla } from '@/components/ui/Pantalla';
import { Tarjeta } from '@/components/ui/Tarjeta';
import { Texto } from '@/components/ui/Texto';
import { api, desenvolver, mensajeDeError, type Esquemas } from '@/lib/api';
import { useUsuarios } from '@/lib/consultas';
import { horaCorta, hoyIso } from '@/lib/formato';

type Tipo = Esquemas['TipoDocumento'];
type Documento = Esquemas['DocumentoSalida'];

const TIPOS: { valor: Tipo; etiqueta: string; detalle: string }[] = [
  {
    valor: 'hoja_pedidos',
    etiqueta: 'Hoja de pedidos',
    detalle: 'A4 apaisada, por turno y preventista',
  },
  { valor: 'remitos', etiqueta: 'Remitos', detalle: 'Igual al talonario: 4 por hoja A4 o de a uno en 10 × 15' },
  {
    valor: 'hoja_ruta',
    etiqueta: 'Hoja de ruta y rendición',
    detalle: '26 pedidos por hoja por preventista',
  },
  {
    valor: 'tickets',
    etiqueta: 'Tickets de preparación',
    detalle: 'Comandera 80 mm, un casillero por caja',
  },
  { valor: 'consolidado', etiqueta: 'Consolidado Excel', detalle: 'Una fila por pedido' },
];

/** Abre, comparte o imprime: en web se abre la URL firmada; en el celular, expo-sharing/print. */
async function abrir(documento: Documento, modo: 'abrir' | 'compartir' | 'imprimir') {
  if (!documento.url) return;
  if (Platform.OS === 'web' || modo === 'abrir') {
    await Linking.openURL(documento.url);
    return;
  }
  const FileSystem = await import('expo-file-system/legacy');
  const destino = `${FileSystem.cacheDirectory}${documento.nombre_archivo}`;
  await FileSystem.downloadAsync(documento.url, destino);
  if (modo === 'imprimir' && documento.nombre_archivo.endsWith('.pdf')) {
    const Print = await import('expo-print');
    await Print.printAsync({ uri: destino });
  } else {
    const Sharing = await import('expo-sharing');
    await Sharing.shareAsync(destino);
  }
}

export default function Imprimir() {
  const queryClient = useQueryClient();
  const [fecha, setFecha] = useState(hoyIso());
  const [turno, setTurno] = useState<'manana' | 'tarde' | null>(null);
  const [preventista, setPreventista] = useState<string | null>(null);
  const [formato, setFormato] = useState<'a4' | '10x15'>('a4');
  const usuarios = useUsuarios();
  const documentos = useQuery({
    queryKey: ['documentos', fecha],
    refetchInterval: (q) => (q.state.data?.some((d) => d.estado === 'pendiente') ? 2000 : false),
    queryFn: async () =>
      desenvolver(await api.GET('/documentos', { params: { query: { fecha } } })),
  });
  const solicitar = useMutation({
    mutationFn: async (tipo: Tipo) =>
      desenvolver(
        await api.POST('/documentos', {
          body: { tipo, fecha, turno, preventista_id: preventista, formato },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documentos', fecha] }),
  });

  return (
    <Pantalla sinNav refrescando={documentos.isFetching} onRefrescar={() => documentos.refetch()}>
      <SelectorFecha valor={fecha} onCambio={setFecha} />
      <Seccion titulo="Imprimir" detalle="Todo se genera en el servidor y queda archivado.">
        <Chips
          opciones={[
            { valor: 'manana', etiqueta: 'Mañana' },
            { valor: 'tarde', etiqueta: 'Tarde' },
          ]}
          valor={turno}
          onCambio={setTurno}
        />
        <Chips
          opciones={(usuarios.data ?? [])
            .filter((u) => u.rol === 'preventista')
            .map((u) => ({ valor: u.id, etiqueta: u.nombre }))}
          valor={preventista}
          onCambio={setPreventista}
        />
        <Chips
          opciones={[
            { valor: 'a4', etiqueta: 'Remitos: 4 por hoja A4' },
            { valor: '10x15', etiqueta: 'Remitos: talonario 10 × 15' },
          ]}
          valor={formato}
          onCambio={(v) => setFormato(v ?? 'a4')}
          permitirNinguno={false}
        />
      </Seccion>
      <View className="flex-row flex-wrap gap-3">
        {TIPOS.map((t) => (
          <View key={t.valor} className="min-w-[260px] flex-1">
            <Tarjeta>
              <Texto variante="headline-md">{t.etiqueta}</Texto>
              <Texto variante="body-md" tono="suave">
                {t.detalle}
              </Texto>
              <View className="mt-3">
                <Boton
                  texto="Generar"
                  icono="file-document"
                  variante="secundario"
                  onPress={() => solicitar.mutate(t.valor)}
                  cargando={solicitar.isPending && solicitar.variables === t.valor}
                />
              </View>
            </Tarjeta>
          </View>
        ))}
      </View>
      {solicitar.isError ? (
        <Texto variante="body-md" tono="peligro">
          {mensajeDeError(solicitar.error)}
        </Texto>
      ) : null}
      {documentos.isError && !documentos.data ? (
        <ErrorCarga error={documentos.error} onReintentar={() => documentos.refetch()} />
      ) : null}
      <Seccion titulo="Generados" detalle="Los más nuevos primero">
        <Tabla<Documento>
          columnas={[
            {
              clave: 'hora',
              titulo: 'Hora',
              ancho: 70,
              render: (d) => <Texto variante="body-md">{horaCorta(d.creado_en)}</Texto>,
            },
            {
              clave: 'archivo',
              titulo: 'Archivo',
              ancho: 260,
              render: (d) => (
                <Texto variante="body-lg" numberOfLines={1}>
                  {d.nombre_archivo}
                </Texto>
              ),
            },
            {
              clave: 'estado',
              titulo: 'Estado',
              ancho: 120,
              render: (d) => (
                <Badge
                  estado={
                    d.estado === 'listo'
                      ? 'entregado'
                      : d.estado === 'error'
                        ? 'cancelado'
                        : 'pendiente'
                  }
                  texto={
                    d.estado === 'listo' ? 'Listo' : d.estado === 'error' ? 'Error' : 'Generando'
                  }
                />
              ),
            },
            {
              clave: 'acciones',
              titulo: 'Acciones',
              ancho: 320,
              render: (d) =>
                d.estado === 'listo' ? (
                  <View className="flex-row gap-1">
                    <Boton
                      texto="Abrir"
                      variante="ghost"
                      compacto
                      icono="open-in-new"
                      onPress={() => abrir(d, 'abrir')}
                    />
                    {Platform.OS !== 'web' ? (
                      <Boton
                        texto="Compartir"
                        variante="ghost"
                        compacto
                        icono="share-variant"
                        onPress={() => abrir(d, 'compartir')}
                      />
                    ) : null}
                    {Platform.OS !== 'web' && d.nombre_archivo.endsWith('.pdf') ? (
                      <Boton
                        texto="Imprimir"
                        variante="ghost"
                        compacto
                        icono="printer"
                        onPress={() => abrir(d, 'imprimir')}
                      />
                    ) : null}
                  </View>
                ) : (
                  <Texto variante="body-md" tono={d.error ? 'peligro' : 'suave'}>
                    {d.error ?? '…'}
                  </Texto>
                ),
            },
          ]}
          filas={documentos.data ?? []}
          claveDe={(d) => d.id}
        />
      </Seccion>
    </Pantalla>
  );
}

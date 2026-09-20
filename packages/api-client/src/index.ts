import createClient from 'openapi-fetch';

import type { paths } from './schema';

export type { components, paths } from './schema';

/** Cliente tipado contra el OpenAPI de la API. Si cambia un campo en el servidor, la app deja de compilar. */
export function crearClienteApi(baseUrl: string, obtenerToken?: () => string | null) {
  const cliente = createClient<paths>({ baseUrl });
  cliente.use({
    onRequest({ request }) {
      const token = obtenerToken?.();
      if (token) request.headers.set('Authorization', `Bearer ${token}`);
      return request;
    },
  });
  return cliente;
}

export type ClienteApi = ReturnType<typeof crearClienteApi>;

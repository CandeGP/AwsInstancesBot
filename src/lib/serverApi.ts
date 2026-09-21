// Cliente HTTP de la API de control del servidor (API Gateway -> Lambda -> EC2).
// La URL base y la API key salen de SERVER_API_URL / SERVER_API_KEY (ver .env.example).

export interface ServerInfo {
  instance_id: string;
  state: string;
  instance_type: string;
  public_ip: string | null;
  game_port: number;
  launch_time: string | null;
  changed?: boolean;
  message: string;
}

// Error con un mensaje apto para mostrarse al usuario en Discord.
export class ServerApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = 'ServerApiError';
  }
}

const REQUEST_TIMEOUT_MS = 20_000;

async function request(method: 'GET' | 'POST', path: string): Promise<ServerInfo> {
  const baseUrl = process.env.SERVER_API_URL;
  const apiKey = process.env.SERVER_API_KEY;
  if (!baseUrl || !apiKey) {
    throw new ServerApiError('La API del servidor no esta configurada (SERVER_API_URL / SERVER_API_KEY).');
  }

  let response: Response;
  try {
    response = await fetch(`${baseUrl.replace(/\/$/, '')}${path}`, {
      method,
      headers: { 'x-api-key': apiKey },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch {
    throw new ServerApiError('No pude comunicarme con la API del servidor (sin respuesta o tiempo agotado).');
  }

  const body = (await response.json().catch(() => ({}))) as Partial<ServerInfo>;
  if (!response.ok) {
    // 403 lo devuelve API Gateway cuando la API key es invalida.
    const detail = response.status === 403 ? 'API key invalida o sin permisos.' : (body.message ?? `HTTP ${response.status}`);
    throw new ServerApiError(detail, response.status);
  }
  return body as ServerInfo;
}

export const getServerStatus = () => request('GET', '/server');
export const startServer = () => request('POST', '/server/start');
export const stopServer = () => request('POST', '/server/stop');

const STATE_LABELS: Record<string, string> = {
  running: '🟢 Encendido',
  pending: '🟡 Arrancando',
  stopping: '🟠 Apagandose',
  stopped: '🔴 Apagado',
  'shutting-down': '⚫ Eliminandose',
  terminated: '⚫ Eliminado',
};

// Texto multilinea con el estado del servidor, listo para enviarse a Discord.
export function formatServerInfo(info: ServerInfo): string {
  const lines = [`**Servidor:** ${STATE_LABELS[info.state] ?? info.state} (${info.instance_type})`];
  if (info.public_ip) {
    lines.push(`**Direccion:** \`${info.public_ip}:${info.game_port}\``);
  }
  return lines.join('\n');
}

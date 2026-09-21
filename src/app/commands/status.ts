import type { ChatInputCommand, CommandData } from 'commandkit';
import { ServerApiError, formatServerInfo, getServerStatus } from '../../lib/serverApi';

// Descripcion del bot, se muestra en discord cuando se pone /status
export const command: CommandData = {
  name: 'status',
  description: 'Muestra el estado del bot y del servidor de juego.',
};

// Comando que se ejecuta cuando se pone /status
export const chatInput: ChatInputCommand = async ({ interaction }) => {
  await interaction.deferReply();

  const botLine = `Bot online. Latencia: ${interaction.client.ws.ping} ms.`;
  try {
    const info = await getServerStatus();
    await interaction.editReply(`${botLine}\n${formatServerInfo(info)}`);
  } catch (error) {
    // El bot esta vivo aunque la API falle: se informa ambas cosas por separado.
    const reason = error instanceof ServerApiError ? error.message : 'error inesperado';
    if (!(error instanceof ServerApiError)) console.error('[status]', error);
    await interaction.editReply(`${botLine}\n⚠️ No pude consultar el servidor: ${reason}`);
  }
};

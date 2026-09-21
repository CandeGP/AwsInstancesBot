import type { ChatInputCommand, CommandData } from 'commandkit';
import { stopServer } from '../../lib/serverApi';
import { runServerAction } from '../../lib/serverAction';

export const command: CommandData = {
  name: 'stopserver',
  description: 'Apaga el servidor de juego.',
  dm_permission: false,
};

// Cualquier miembro del servidor de Discord puede usarlo (no funciona por mensaje directo)
export const chatInput: ChatInputCommand = async ({ interaction }) => {
  await runServerAction(interaction, stopServer);
};

import type { ChatInputCommand, CommandData } from 'commandkit';
import { startServer } from '../../lib/serverApi';
import { runServerAction } from '../../lib/serverAction';

export const command: CommandData = {
  name: 'startserver',
  description: 'Enciende el servidor de juego.',
  dm_permission: false,
};

// Cualquier miembro del servidor de Discord puede usarlo (no funciona por mensaje directo)
export const chatInput: ChatInputCommand = async ({ interaction }) => {
  await runServerAction(interaction, startServer);
};

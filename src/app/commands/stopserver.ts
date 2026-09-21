import type { ChatInputCommand, CommandData } from 'commandkit';
import { stopServer } from '../../lib/serverApi';
import { runServerAction } from '../../lib/serverAction';

export const command: CommandData = {
  name: 'stopserver',
  description: 'Apaga el servidor de juego.',
};

// Solo administradores o roles en ADMIN_ROLE_IDS (ver src/lib/serverAction.ts)
export const chatInput: ChatInputCommand = async ({ interaction }) => {
  await runServerAction(interaction, stopServer);
};

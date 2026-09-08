import type { ChatInputCommand, CommandData } from 'commandkit';

// Descripcion del bot, se muestra en discord cuando se pone /status
export const command: CommandData = {
  name: 'status',
  description: 'Muestra el estado del bot.',
};

// Comando que se ejecuta cuando se pone /status
export const chatInput: ChatInputCommand = async ({ interaction }) => {
  await interaction.reply(`Bot online. Latencia: ${interaction.client.ws.ping} ms.`);
};
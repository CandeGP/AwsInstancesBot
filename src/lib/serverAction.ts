import type { ChatInputCommand } from 'commandkit';
import { MessageFlags, PermissionFlagsBits } from 'discord.js';
import { formatServerInfo, type ServerInfo } from './serverApi';
import { UserError } from './userError';

// Tipo de la interaccion tal como la entrega CommandKit (evita duplicar los tipos de discord.js).
export type Interaction = Parameters<ChatInputCommand>[0]['interaction'];

function isDiscordAdmin(interaction: Interaction): boolean {
  const member = interaction.inGuild() ? interaction.member : null;
  return !!member && typeof member.permissions !== 'string' && member.permissions.has(PermissionFlagsBits.Administrator);
}

// Flujo comun de los comandos que actuan sobre AWS: valida el contexto, ejecuta la accion y
// responde con el texto que devuelva. Solo funcionan dentro de un servidor de Discord; con
// `adminOnly` ademas exigen el permiso de Administrador de Discord.
// Se usa deferReply porque las acciones pueden tardar mas de los 3 s que da Discord.
// Los UserError se muestran tal cual; cualquier otro error se registra y se responde generico.
export async function runCommand(
  interaction: Interaction,
  action: () => Promise<string>,
  options: { adminOnly?: boolean } = {},
): Promise<void> {
  if (!interaction.inGuild()) {
    await interaction.reply({
      content: 'Este comando solo funciona dentro de un servidor.',
      flags: MessageFlags.Ephemeral,
    });
    return;
  }
  if (options.adminOnly && !isDiscordAdmin(interaction)) {
    await interaction.reply({
      content: '⛔ Este comando es solo para administradores del servidor.',
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  await interaction.deferReply();
  try {
    // allowedMentions vacio: el texto nunca debe pingear roles ni usuarios.
    await interaction.editReply({ content: await action(), allowedMentions: { parse: [] } });
  } catch (error) {
    if (!(error instanceof UserError)) console.error('[command]', error);
    const message = error instanceof UserError ? error.message : 'Error inesperado al ejecutar el comando.';
    await interaction.editReply({ content: `❌ ${message}`, allowedMentions: { parse: [] } });
  }
}

// /startserver y /stopserver: ejecuta la accion sobre el servidor y muestra su estado.
export function runServerAction(interaction: Interaction, action: () => Promise<ServerInfo>): Promise<void> {
  return runCommand(interaction, async () => {
    const info = await action();
    return `${info.message}\n${formatServerInfo(info)}`;
  });
}

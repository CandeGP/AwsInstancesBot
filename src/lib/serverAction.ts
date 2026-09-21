import type { ChatInputCommand } from 'commandkit';
import { MessageFlags, PermissionFlagsBits } from 'discord.js';
import { ServerApiError, formatServerInfo, type ServerInfo } from './serverApi';

// Tipo de la interaccion tal como la entrega CommandKit (evita duplicar los tipos de discord.js).
type Interaction = Parameters<ChatInputCommand>[0]['interaction'];

// Puede ejecutar acciones sensibles quien sea administrador del servidor de Discord
// o tenga alguno de los roles listados (separados por coma) en ADMIN_ROLE_IDS.
export function canControlServer(interaction: Interaction): boolean {
  const member = interaction.inGuild() ? interaction.member : null;
  if (!member || typeof member.permissions === 'string') return false;

  if (member.permissions.has(PermissionFlagsBits.Administrator)) return true;

  const allowedRoles = (process.env.ADMIN_ROLE_IDS ?? '')
    .split(',')
    .map((id) => id.trim())
    .filter(Boolean);
  const memberRoles = Array.isArray(member.roles) ? member.roles : [...member.roles.cache.keys()];
  return memberRoles.some((roleId) => allowedRoles.includes(roleId));
}

// Flujo comun de /startserver y /stopserver: valida permisos, llama a la API y responde.
// Se usa deferReply porque encender/apagar puede tardar mas de los 3 s que da Discord.
export async function runServerAction(
  interaction: Interaction,
  action: () => Promise<ServerInfo>,
): Promise<void> {
  if (!canControlServer(interaction)) {
    await interaction.reply({
      content: '⛔ No tienes permisos para controlar el servidor.',
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  await interaction.deferReply();
  try {
    const info = await action();
    await interaction.editReply(`${info.message}\n${formatServerInfo(info)}`);
  } catch (error) {
    const message = error instanceof ServerApiError ? error.message : 'Error inesperado al controlar el servidor.';
    if (!(error instanceof ServerApiError)) console.error('[server-action]', error);
    await interaction.editReply(`❌ ${message}`);
  }
}

import type { ChatInputCommand, CommandData } from 'commandkit';
import { ApplicationCommandOptionType, ChannelType, PermissionFlagsBits } from 'discord.js';
import { runCommand, type Interaction } from '../../lib/serverAction';
import { setNotificationWebhook } from '../../lib/serverApi';
import { UserError } from '../../lib/userError';

// Codigo de error de Discord cuando al bot le falta un permiso (Missing Permissions).
const MISSING_PERMISSIONS = 50013;

export const command: CommandData = {
  name: 'notificaciones',
  description: 'Elige el canal donde se publican los avisos del servidor (encendido, apagado y fallos).',
  // Discord oculta el comando a quien no sea administrador; runCommand lo vuelve a comprobar.
  default_member_permissions: PermissionFlagsBits.Administrator.toString(),
  dm_permission: false,
  options: [
    {
      type: ApplicationCommandOptionType.Channel,
      name: 'canal',
      description: 'Canal de texto que recibira las notificaciones.',
      required: true,
      channel_types: [ChannelType.GuildText, ChannelType.GuildAnnouncement],
    },
  ],
};

// El bot crea un webhook en el canal elegido y lo guarda en AWS a traves de la API;
// la URL del webhook es un secreto y no se muestra.
async function configureNotifications(interaction: Interaction): Promise<string> {
  const selected = interaction.options.getChannel('canal', true);
  const channel = await interaction.guild?.channels.fetch(selected.id);
  if (!channel || !('createWebhook' in channel)) {
    throw new UserError('Elige un canal de texto de este servidor.');
  }

  let webhook;
  try {
    webhook = await channel.createWebhook({
      name: 'AwsInstancesBot',
      reason: `Notificaciones configuradas por ${interaction.user.tag}`,
    });
  } catch (error) {
    if ((error as { code?: number }).code === MISSING_PERMISSIONS) {
      throw new UserError(`Me falta el permiso **Gestionar webhooks** en <#${channel.id}>.`);
    }
    throw error;
  }

  try {
    await setNotificationWebhook(webhook.url);
  } catch (error) {
    // No dejar un webhook huerfano en el canal si AWS no lo pudo guardar.
    await webhook.delete('No se pudo guardar el webhook en AWS').catch(() => undefined);
    throw error;
  }

  // Mensaje de prueba en el canal; si falla no invalida la configuracion ya guardada.
  await webhook
    .send('✅ Este canal recibira los avisos del servidor: encendido, apagado y fallos de salud.')
    .catch((error) => console.error('[notificaciones] mensaje de prueba', error));

  return `✅ Notificaciones configuradas en <#${channel.id}>.`;
}

// Solo administradores de Discord: cambia a donde van los avisos del servidor.
export const chatInput: ChatInputCommand = async ({ interaction }) => {
  await runCommand(interaction, () => configureNotifications(interaction), { adminOnly: true });
};

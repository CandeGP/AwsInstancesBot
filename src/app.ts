import { Client, GatewayIntentBits } from 'discord.js';

// Configuracion del cliente de discord
const client = new Client({
  intents: [GatewayIntentBits.Guilds],
});

client.token = process.env.DISCORD_TOKEN ?? null;

export default client;
//importante: no eliminar la carpeta EVENTS, ya que es donde se guardan los eventos del bot y commandkit los busca automaticamente, de lo contrario no funcionara el bot
// Evento que se ejecuta en consola cuando el bot se conecta a discord, sirve para comprobar que este vivo (como zimba)
export const event = {
  name: 'ready',
};

export const run = ({ client }: { client: any }) => {
  console.log(`✅ Bot conectado como: ${client.user.tag}`);
};

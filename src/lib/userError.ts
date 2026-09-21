// Error cuyo mensaje es seguro y util para mostrarse tal cual al usuario en Discord.
// Cualquier otro error se registra en consola y se responde con un mensaje generico.
export class UserError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'UserError';
  }
}

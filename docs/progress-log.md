# Registro de progreso

## 2026-09-18 — Dockerizar el bot para ejecución persistente

**Contexto:** el bot solo se ejecutaba con `npm run dev`/`npm start` en una terminal local, por lo que había que volver a levantarlo manualmente en cada sesión de trabajo para poder probar comandos.

**Estado anterior:** `docker/` existía como carpeta vacía; el README documentaba `docker-compose up --build` pero no había `Dockerfile` ni `docker-compose.yml` reales.

**Estado nuevo:**
- `docker/Dockerfile`: imagen `node:20-alpine`, instala dependencias con `npm ci`, compila con `npm run build` y arranca con `npm start` (CommandKit).
- `docker/docker-compose.yml`: servicio `bot` con `context: ..`, `env_file: ../.env` y `restart: unless-stopped` para que el contenedor se mantenga activo sin intervención manual.
- `.dockerignore`: excluye `node_modules/`, `dist/`, `.git/`, `.env`, `infra/`, `cdk.out/`, `docs/`, `.claude/` del contexto de build.
- `README.md`: instrucción de instalación actualizada a `docker compose -f docker/docker-compose.yml up --build -d`, con notas de `logs -f` y `down`.

**Archivos modificados:** `docker/Dockerfile` (nuevo), `docker/docker-compose.yml` (nuevo), `.dockerignore` (nuevo), `README.md`.

**Validación:** no se pudo ejecutar `docker build`/`docker compose up` porque esta máquina no tiene Docker instalado (`docker: command not found`). Sí se validó localmente que `npm run build` y `npm start` funcionan fuera de contenedor (el bot carga `.env`, registra el comando `/status` y refresca los comandos de aplicación en Discord), por lo que el mismo flujo dentro del `Dockerfile` debería comportarse igual. Pendiente: correr `docker compose -f docker/docker-compose.yml up --build` en una máquina con Docker antes de considerar esto validado end-to-end.

**Riesgos y decisiones pendientes:**
- No se agregó `HEALTHCHECK` ni límites de recursos al contenedor; evaluar si se necesita para producción.
- El contenedor no expone puertos (el bot no los necesita), pero si se agrega un panel de salud/monitoreo (Fase 4) habrá que revisar el compose.
- Sigue pendiente el resto de la Fase 2 (AutoStart) y la Fase 3 (conectar el bot con AWS SDK para `/startserver`, `/stopserver`, `/upgrade`), no relacionado con este cambio.

**Próximo criterio de aceptación:** ejecutar `docker compose -f docker/docker-compose.yml up --build -d` en una máquina con Docker Desktop/Engine y confirmar en los logs que el bot se conecta a Discord y responde `/status`.

## 2026-09-21 — Nombre del proyecto Docker y validación del despliegue

**Contexto:** tras desplegar el bot en Docker Desktop, el grupo aparecía como `docker` porque Compose toma por defecto el nombre de la carpeta del `docker-compose.yml`.

**Estado anterior:** proyecto `docker`, contenedor `docker-bot-1`.

**Estado nuevo:** `docker/docker-compose.yml` define `name: aws-instances-bot`, `container_name: aws-instances-bot` e `image: aws-instances-bot:latest`. El servicio sigue llamándose `bot`, así que los comandos del README no cambian.

**Archivos modificados:** `docker/docker-compose.yml`.

**Validación:** `docker ps` muestra el contenedor `aws-instances-bot` en estado `Up`; `docker compose ls` lista el proyecto `aws-instances-bot`; los logs muestran "Loaded 1 commands", "Refreshed 1 global application (/) commands" y `[status] Command executed successfully`. Con esto queda cumplido el criterio de aceptación de la entrada del 2026-09-18 (Docker validado end-to-end para `/status`).

**Riesgos y decisiones pendientes:**
- Cambiar `name:` crea un proyecto nuevo; el contenedor `docker-bot-1` anterior debe eliminarse con `down` si aún existe.
- Warning `MODULE_TYPELESS_PACKAGE_JSON` en los logs: cosmético, se resuelve con `"type": "module"` en `package.json` (no aplicado, requiere comprobar que el build sigue funcionando).

## 2026-09-21 — Cierre de la Fase 2: decisiones y protección de la instancia

**Contexto:** revisión del roadmap contra el repositorio. Se tomaron decisiones para dar por cerrada la Fase 2 y pasar a la Fase 3.

**Decisiones:**
- **AutoStart: descartado.** La instancia no debe encenderse sola. Solo se enciende con una acción explícita (futuro `/startserver`).
- **VPC:** se mantiene la VPC por defecto.
- **AutoStop:** se deja como está (por CPU, `auto_stop_enabled = true`). Probado manualmente por la autora; es una aproximación temporal, no detecta jugadores.
- **Tipo de instancia:** el servidor ya arranca. Subir a una instancia mayor queda para el futuro.
- **Documentación:** se deja como está por ahora, aunque `terraform-ec2-setup.md` difiere de `variables.tf` (`t3.medium`/`false`/40 GB en la doc contra `t3.micro`/`true`/20 GB en el código).

**Problema detectado:** `deploy-infra.yml` hace `terraform apply` en cada push a `main`. Terraform no recrea la instancia si ya existe (el estado está en S3), pero había dos riesgos: `data.aws_ami.ubuntu` usa `most_recent`, así que una AMI nueva de Canonical cambiaría `ami` y reemplazaría la instancia (con `delete_on_termination = true`, se perdería el mundo); y un cambio en `user_data` detiene y arranca la instancia sin volver a ejecutar el bootstrap. Además, el workflow corría con cambios de código del bot o de documentación que no afectan a la infraestructura.

**Estado nuevo:**
- `infra/main.tf`: `lifecycle { ignore_changes = [ami, user_data] }` en `aws_instance.game_server`.
- `.github/workflows/deploy-infra.yml`: el push solo dispara el despliegue si cambian `infra/**` (sin `infra/CDK/**`), `lambdas/**`, `scripts/ec2-user-data.sh` o el propio workflow; `workflow_dispatch` sigue disponible; `concurrency` evita dos despliegues a la vez.

**Archivos modificados:** `infra/main.tf`, `.github/workflows/deploy-infra.yml`, `docs/progress-log.md`.

**Validación:** `terraform fmt -check` y `terraform validate` pasan. No se ejecutó `terraform plan` (requiere backend S3 y credenciales); el primer despliegue tras el push debería mostrar cero cambios sobre la instancia. El YAML del workflow no se validó con un parser local.

**Riesgos y decisiones pendientes:**
- Con `ignore_changes` sobre `ami`, para cambiar de AMI o reinstalar hay que reemplazar la instancia a propósito (`terraform apply -replace=aws_instance.game_server`), asumiendo pérdida de datos si no hay backup.
- Cuando exista `/upgrade`, cambiar el tipo de instancia fuera de Terraform generará drift; habrá que decidir si Terraform lo ignora (`ignore_changes` en `instance_type`) o si sigue siendo la fuente de verdad.
- `apply -auto-approve` sigue activo por decisión explícita; no hay backups del mundo del juego.

**Próximo criterio de aceptación:** Fase 3, empezando por el endpoint de solo lectura `GET /status` (ver diseño acordado en la conversación: Discord bot → API Gateway → Lambda Python → EC2).

## 2026-09-21 — Fase 3: cadena bot → API Gateway → Lambda → EC2

**Contexto:** con la Fase 2 cerrada, se implementó el flujo de control del servidor desde Discord. Antes, `/status` solo mostraba la latencia del bot y no existía ninguna conexión con AWS.

**Estado nuevo:**
- `lambdas/server_control/` (Python 3.12): `handler.py` enruta las peticiones de API Gateway y `ec2_service.py` contiene la lógica (consultar estado, encender, apagar). Las operaciones son idempotentes: encender un servidor encendido no falla y responde `changed: false`; si la instancia está en transición (`stopping`, `pending`) responde 409.
- `infra/control_api.tf`: Lambda con rol propio de mínimo privilegio (`StartInstances`/`StopInstances` restringidos al ARN de la instancia, `DescribeInstances` sin restricción porque AWS no lo permite), log group con retención de 14 días, API REST en API Gateway con rutas `GET /server`, `POST /server/start` y `POST /server/stop`, API key obligatoria, usage plan (5 req/s, ráfaga 10, 1000 req/día) y stage `v1`. El ID de la instancia se inyecta a la Lambda como `INSTANCE_ID`.
- `infra/outputs.tf`: `server_api_url`, `server_api_key` (sensible) y `server_control_lambda_name`.
- Bot: `src/lib/serverApi.ts` (cliente HTTP con timeout y errores legibles), `src/lib/serverAction.ts` (permisos por rol y flujo común de respuesta), comandos `/startserver` y `/stopserver` nuevos, y `/status` ahora incluye el estado del servidor (sigue respondiendo aunque la API falle).
- Permisos: solo administradores del servidor de Discord o roles en `ADMIN_ROLE_IDS` pueden encender o apagar; `/status` es público.
- `.env.example`, `README.md` (comandos y conexión con AWS) y `docs/architecture.md` (API Gateway en los diagramas) actualizados.

**Archivos modificados:** `lambdas/server_control/handler.py`, `lambdas/server_control/ec2_service.py`, `lambdas/tests/test_server_control.py`, `infra/control_api.tf`, `infra/outputs.tf`, `src/lib/serverApi.ts`, `src/lib/serverAction.ts`, `src/app/commands/startserver.ts`, `src/app/commands/stopserver.ts`, `src/app/commands/status.ts`, `.env.example`, `README.md`, `docs/architecture.md`, `docs/progress-log.md`.

**Validación:**
- 12 pruebas unitarias de la Lambda con un cliente EC2 falso (`python -m unittest discover -s lambdas/tests -t lambdas -v`): pasan.
- `terraform validate` y `terraform fmt -check` pasan con Terraform 1.6.6 (la versión del workflow), ejecutados en un contenedor Docker. En esta máquina `terraform validate` falla en local porque el antivirus (Norton) intercepta el TLS entre Terraform y sus plugins (`x509: certificate signed by unknown authority`); es la misma causa que rompió `git push`.
- `tsc --noEmit` y `npm run build` pasan. El cliente HTTP se probó contra un servidor simulado (200, 409, 403 y falta de configuración).
- **Validación en producción:** la autora confirmó que el despliegue por GitHub Actions se completó y que el flujo bot → API Gateway → Lambda → EC2 funciona en Discord real. No se registró qué comandos se probaron ni el resultado del `terraform plan`.

**Riesgos y decisiones pendientes:**
- El push a `main` dispara `terraform apply -auto-approve` y crea la API, la Lambda y la API key. Revisar en Actions que el plan no toque `aws_instance.game_server`.
- La API key es un secreto compartido único: quien la tenga puede encender o apagar el servidor sin pasar por Discord. Vive en el estado de Terraform (S3, cifrado) y en el `.env` del bot. Rotarla si se filtra (`terraform apply -replace=aws_api_gateway_api_key.bot`).
- La autorización por rol se valida solo en el bot; la API no distingue usuarios. Suficiente para un solo bot de confianza, insuficiente si se abre la API a otros clientes.
- La IP pública cambia en cada arranque (sin Elastic IP); `/status` la muestra mientras el servidor está encendido.
- `/upgrade` queda fuera: falta decidir cómo manejar el drift del tipo de instancia con Terraform (ver entrada anterior). Tampoco hay aún notificaciones automáticas a Discord (SNS/webhooks) ni cooldown por jugadores.

**Próximo criterio de aceptación:** tras el despliegue, copiar `server_api_url` y `server_api_key` al `.env`, reiniciar el contenedor (`docker compose -f docker/docker-compose.yml up --build -d`) y confirmar en Discord que `/status` muestra el estado real, que `/startserver` lo enciende, que `/stopserver` lo apaga y que un usuario sin rol recibe el mensaje de permisos.

## 2026-09-21 — Fase 3: notificaciones automáticas en Discord

**Contexto:** con el control del servidor funcionando, nadie se enteraba de los cambios que no pasaban por el bot (por ejemplo, cuando AutoStop apagaba la instancia) ni de fallos. Además, `/startserver` responde antes de que exista la IP pública, que cambia en cada arranque.

**Estado nuevo:**
- `lambdas/notifier/` (Python 3.12): `messages.py` (texto de cada evento, sin llamadas a AWS), `webhook.py` (lee la URL desde SSM y publica en Discord) y `handler.py` (orquesta). Errores transitorios (5xx, 429, red) se relanzan para que EventBridge reintente; errores permanentes (4xx) y la falta de configuración solo se registran.
- `infra/notifications.tf` y `infra/control_api.tf`: Lambda con rol de mínimo privilegio, dos reglas de EventBridge (cambios de estado `running`/`stopped`/`terminated` de la instancia y cambios de la alarma de salud) y la alarma `StatusCheckFailed` (3 minutos seguidos fallando; sin datos no cuenta como fallo).
- Motivo del apagado: AutoStop y `/stopserver` escriben el tag temporal `LastStopReason` (`autostop` o `command`) justo antes de apagar; el notifier lo lee, lo incluye en el mensaje y lo borra. Si el tag falla, el apagado continúa igual y el mensaje simplemente no trae el motivo.
- Permisos: `ec2:CreateTags` acotado al ARN de la instancia en la política de AutoStop (`infra/main.tf`) y en la de `server_control`.
- Secreto: la URL del webhook vive en SSM Parameter Store como SecureString (`/discord-bot/aws-instances-bot/webhook-url`). No está en el estado de Terraform, ni en GitHub, ni en variables de entorno de la Lambda.
- **Configuración desde Discord:** `/notificaciones canal:#canal` (solo administradores de Discord). El bot crea un webhook en el canal, lo envía a `PUT /config/notifications` (Lambda `server_control`, módulo `config_service.py`) y publica un mensaje de prueba. La Lambda solo acepta URLs `https://discord.com/api/webhooks/<id>/<token>` (evita apuntar el notifier a otro host), nunca devuelve ni registra la URL y tiene `ssm:PutParameter` (solo escritura) únicamente sobre ese parámetro. Si AWS no puede guardarla, el bot borra el webhook recién creado; si falta el permiso *Gestionar webhooks*, lo explica.
- **Cambio de decisión sobre permisos (reemplaza la línea "Permisos" de la entrada anterior):** cualquier miembro del servidor de Discord puede usar `/startserver`, `/stopserver` y `/status`. Se eliminó `ADMIN_ROLE_IDS`. Los comandos no funcionan por mensaje directo (`dm_permission: false` y comprobación en el bot). `/notificaciones` sigue exigiendo el permiso de Administrador de Discord porque cambia a dónde van los avisos. Se evaluó y se descartó una lista de roles por servidor (DynamoDB y comando `/permisos`); no quedó nada de eso en el código ni en la infraestructura. Las respuestas del bot nunca mencionan (ping) a roles ni usuarios.
- El notifier cachea la URL 5 minutos (TTL), de modo que un cambio de canal se aplica sin redesplegar. El `aws ssm put-parameter` manual sigue siendo válido como alternativa.
- Mensajes: 🟢 encendido (con `IP:puerto`), 🔴 apagado (con motivo si se conoce), ⚫ instancia eliminada, ⚠️ fallo de salud y ✅ recuperación. Las horas se muestran en la zona horaria de cada lector.
- Documentación: `README.md` (sección de notificaciones y creación del parámetro) y `docs/architecture.md` (EventBridge + notifier en lugar de SNS).

**Archivos modificados:** `lambdas/notifier/handler.py`, `lambdas/notifier/messages.py`, `lambdas/notifier/webhook.py`, `lambdas/tests/test_notifier.py`, `lambdas/tests/test_server_control.py`, `lambdas/auto_stop.py`, `lambdas/server_control/ec2_service.py`, `lambdas/server_control/config_service.py`, `lambdas/server_control/handler.py`, `src/app/commands/notificaciones.ts`, `src/lib/serverApi.ts`, `src/lib/serverAction.ts`, `src/lib/userError.ts`, `infra/notifications.tf`, `infra/main.tf`, `infra/control_api.tf`, `infra/outputs.tf`, `README.md`, `docs/architecture.md`, `docs/progress-log.md`.

**Validación:**
- 39 pruebas unitarias (Lambdas `server_control` y `notifier`) sin llamadas a AWS ni a Discord: pasan (`python -m unittest discover -s lambdas/tests -t lambdas -v`). Incluyen que el apagado continúa si falla el tag, que el tag solo se borra si el mensaje se envió, el rechazo de URLs que no son de Discord, que la URL nunca se devuelve y el vencimiento del cache.
- `terraform validate` y `terraform fmt -check` pasan con Terraform 1.6.6 en un contenedor Docker.
- `tsc --noEmit` y `npm run build` pasan. `/notificaciones` se probó con una interacción de Discord simulada contra una API falsa: éxito (crea el webhook y hace `PUT` con la API key), fallo de la API (borra el webhook), bot sin permiso y usuario sin rol (no crea nada).
- **Validación en producción:** tras el despliegue, la autora confirmó que `/notificaciones` funciona en Discord real. No se registró si también se probaron los avisos de encendido y apagado, ni la alarma de salud.
- **Incidente resuelto:** la primera prueba real de `/notificaciones` falló con "Error al comunicarse con AWS". El log de la Lambda mostró `No access to reserved parameter name`: SSM prohíbe nombres de parámetro que empiezan por `aws` o `ssm`, y el original era `/aws-instances-bot/discord-webhook-url`. Se renombró a `/discord-bot/aws-instances-bot/webhook-url` y se añadió una prueba que falla si el nombre vuelve a ser reservado. Ese mensaje ya había aparecido en una prueba local previa y no se reconoció a tiempo.

**Riesgos y decisiones pendientes:**
- **Acción necesaria tras el deploy:** que un administrador ejecute `/notificaciones` (el bot debe tener el permiso *Gestionar webhooks* en el canal elegido). Hasta entonces no llega ninguna notificación; el deploy no falla.
- Cualquier miembro del servidor puede encender el servidor (costo de EC2) y apagarlo aunque haya gente jugando; el único freno es el límite de la API (5 req/s, 1000 al día). Si molesta, la salida más simple es limitar `/stopserver` a un rol.
- Quien tenga la API key puede redirigir las notificaciones a otro webhook de Discord (no a otros hosts). Es un nuevo alcance de la misma clave compartida.
- Al cambiar de canal, el webhook anterior no se borra (no se guarda su ID): queda huérfano en el canal viejo y se puede eliminar a mano desde *Integraciones*.
- El tag `LastStopReason` no está en `aws_instance.game_server`, por lo que un `terraform apply` ejecutado justo entre el apagado y la notificación lo eliminaría (solo se perdería el motivo del mensaje).
- Una falla persistente de Discord agota los reintentos de EventBridge y el mensaje se pierde; no hay cola de mensajes fallidos.
- Al reemplazar la instancia (`-replace`), las reglas y la alarma se actualizan al nuevo ID en el siguiente `apply`.
- Sigue pendiente el cooldown por jugadores (el AutoStop solo mira CPU) y `/upgrade`.

**Próximo criterio de aceptación:** ejecutar `/notificaciones` en el canal deseado y confirmar el mensaje de prueba; con el servidor apagado, ejecutar `/startserver` y confirmar que llega el mensaje 🟢 con la IP; luego `/stopserver` y confirmar el 🔴 con "Se apagó con /stopserver"; y comprobar un apagado por AutoStop con su motivo.

## 2026-09-21 — Diagnóstico del juego: por qué no arrancaba en la instancia

**Contexto:** el servidor de Project Zomboid nunca había arrancado. Se atribuía a la `t3.micro`, y se descartaba un tipo mayor porque AWS lo rechazaba.

**Diagnóstico (por SSM sobre la instancia real, solo lectura y luego un arreglo puntual):**
1. **Error del bootstrap:** `zomboid.service` fallaba en bucle (más de 35 reinicios) con `chown: changing ownership of '/home/steam/zomboid-data': Operation not permitted`. `install -d` crea el directorio padre como `root`, y `start_server.sh` (que corre como `steam`) intentaba hacerle `chown`. La descarga del juego (SteamCMD, 9.6 GB) sí había terminado bien.
2. **Falta de memoria:** corregido lo anterior, el juego avanzó hasta `Initialising Server Systems...` y el kernel lo mató dos veces: `Out of memory: Killed process (ProjectZomboid6...)`. La instancia tiene 909 MB de RAM. Además el bootstrap fijaba el heap de Java en `-Xmx1536m`, más que la RAM total.
3. **Restricción de cuenta:** la cuenta está en el plan gratuito de AWS (`FREE`, 159.19 USD de créditos, vence el 2027-03-03), que solo permite ciertos tipos de instancia. Según `describe-instance-types` con el filtro `free-tier-eligible`, los permitidos son `t3.micro`, `t4g.micro`, `t8i.micro`, `t3.small`, `t4g.small`, `t8i.small`, `c7i-flex.large` (4 GB) y `m7i-flex.large` (8 GB). Por eso `m5.large` fue rechazado, pero `m7i-flex.large` sí es viable sin cambiar de plan.

**Estado nuevo (en el repositorio, pendiente de desplegar):**
- `infra/variables.tf`: `instance_type` por defecto pasa a `m7i-flex.large`. Cambiar el tipo es una modificación en el sitio (se apaga y enciende); el disco y el mundo se conservan.
- `scripts/ec2-user-data.sh`: el bootstrap hace `chown -R steam:steam` de `zomboid-data` como `root`, se quitó el `chown` de `start_server.sh`, y el heap de Java pasa a ser el 50 % de la RAM (máximo 8 GB) en vez de `1536m` fijo. Por `ignore_changes = [user_data]`, esto solo afecta a instancias nuevas.

**Cambios manuales en la instancia existente (no están en Terraform):** `chown -R steam:steam /home/steam/zomboid-data` y, tras el resize, `-Xmx4096m` en `/home/steam/zomboid/ProjectZomboid64.json` (el `user_data` no se vuelve a ejecutar) con reinicio del servicio.

**Resultado del cambio de tipo (push `f31aeb4`, `terraform apply` por Actions):** la instancia pasó a `m7i-flex.large` con 7 776 MB de RAM y Terraform la dejó encendida. Se midió el heap: con `-Xmx5832m` (75 %) el juego arrancó (`*** SERVER STARTED ****`, UDP 16261 y 16262 en escucha, sin OOM) pero quedaban solo ~480 MB disponibles sin jugadores, porque el juego usa ZGC, que compromete todo el heap, y ~1 GB adicional fuera de él. Con `-Xmx4096m` quedan ~2 170 MB disponibles y el proceso ocupa ~5.1 GB. Por eso el script usa el 50 %.

**Validación:** `bash -n` del script y `terraform validate`/`fmt` con 1.6.6 pasan. En la instancia real (por SSM): el resize por Terraform funcionó, el servicio queda `active`, escucha en 16261 y 16262 y no hay OOM. **No validado:** conectarse desde el cliente del juego, el `user_data` corregido en una instancia nueva (solo se verificó su sintaxis) y el comportamiento con jugadores reales.

**Riesgos y decisiones pendientes:**
- Un cambio de `instance_type` por Terraform apaga la instancia; el `apply` no debe coincidir con jugadores conectados.
- El cambio del heap en el script no altera la instancia existente: hay que editar `ProjectZomboid64.json` a mano o reemplazar la instancia (perdiendo el mundo).
- Sigue sin haber backups del mundo.
- El AutoStop por CPU no distingue jugadores; con el juego corriendo puede apagarlo con gente conectada y quietos.


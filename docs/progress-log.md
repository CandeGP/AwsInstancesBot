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
- **No validado:** `terraform plan/apply` (requiere credenciales y backend S3), la Lambda desplegada y los comandos en Discord real.

**Riesgos y decisiones pendientes:**
- El push a `main` dispara `terraform apply -auto-approve` y crea la API, la Lambda y la API key. Revisar en Actions que el plan no toque `aws_instance.game_server`.
- La API key es un secreto compartido único: quien la tenga puede encender o apagar el servidor sin pasar por Discord. Vive en el estado de Terraform (S3, cifrado) y en el `.env` del bot. Rotarla si se filtra (`terraform apply -replace=aws_api_gateway_api_key.bot`).
- La autorización por rol se valida solo en el bot; la API no distingue usuarios. Suficiente para un solo bot de confianza, insuficiente si se abre la API a otros clientes.
- La IP pública cambia en cada arranque (sin Elastic IP); `/status` la muestra mientras el servidor está encendido.
- `/upgrade` queda fuera: falta decidir cómo manejar el drift del tipo de instancia con Terraform (ver entrada anterior). Tampoco hay aún notificaciones automáticas a Discord (SNS/webhooks) ni cooldown por jugadores.

**Próximo criterio de aceptación:** tras el despliegue, copiar `server_api_url` y `server_api_key` al `.env`, reiniciar el contenedor (`docker compose -f docker/docker-compose.yml up --build -d`) y confirmar en Discord que `/status` muestra el estado real, que `/startserver` lo enciende, que `/stopserver` lo apaga y que un usuario sin rol recibe el mensaje de permisos.

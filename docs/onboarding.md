# Guía de incorporación y pruebas

Para quien entra al proyecto con un usuario IAM propio y va a probar, operar y desplegar infraestructura.

## 1. Acceso a AWS

| Dato | Valor |
| --- | --- |
| Consola | https://336425345125.signin.aws.amazon.com/console |
| Región | `us-east-1` |
| Permisos | `AdministratorAccess` (grupo `proyecto-admins`) |

La contraseña temporal te la pasan por privado; AWS te obliga a cambiarla en el primer login.

Antes de hacer nada más:

1. Activa **MFA**: IAM → Users → tu usuario → *Security credentials* → *Assign MFA device*.
2. Crea tu **access key** en la misma pantalla (caso de uso: *Command Line Interface*). El secreto se muestra una sola vez; no lo pegues en chats ni lo subas a git.
3. Configura el perfil local:

```bash
aws configure --profile moi        # region: us-east-1, output: json
export AWS_PROFILE=moi             # PowerShell: $env:AWS_PROFILE = "moi"
aws sts get-caller-identity        # debe mostrar tu usuario, no Terraform-local
```

## 2. Herramientas

- AWS CLI v2
- Terraform **1.6.6** (la misma versión que usa el pipeline)
- Node.js 20+ y npm
- Python 3.10+ (tests de las Lambdas)
- Docker (opcional, para correr el bot)

## 3. Clonar y verificar

```bash
git clone https://github.com/CandeGP/AwsInstancesBot.git
cd AwsInstancesBot
npm ci
python -m unittest discover -s lambdas/tests -t lambdas -v   # tests de las Lambdas
```

## 4. Terraform

El estado es **remoto y compartido** con el pipeline y con el resto del equipo:

| Backend | Valor |
| --- | --- |
| Bucket S3 | `aws-instances-bot-tfstate` |
| Key | `aws-instances-bot/terraform.tfstate` |
| Tabla de lock | `aws-instances-bot-locks` (DynamoDB) |
| Región | `us-east-1` |

```bash
terraform -chdir=infra init \
  -backend-config="bucket=aws-instances-bot-tfstate" \
  -backend-config="key=aws-instances-bot/terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="dynamodb_table=aws-instances-bot-locks" \
  -backend-config="encrypt=true"

terraform -chdir=infra validate
terraform -chdir=infra plan
```

> **No copies `terraform.tfvars.example` tal cual.** Trae `instance_type = "t3.micro"` y `root_volume_size_gb = 20`, valores que no coinciden con los defaults reales (`m7i-flex.large`, 40 GB). Aplicarlo cambiaría el tipo de instancia y el servidor de Project Zomboid se queda sin memoria. Los defaults de `variables.tf` ya son los de producción: no necesitas `tfvars` para operar.

### Antes de aplicar

- Lee siempre el `plan` completo. Cualquier `must be replaced` o `destroy` sobre `aws_instance.game_server` implica **perder el disco del servidor de juego**.
- Evita `apply` desde tu máquina mientras el pipeline esté corriendo (`Actions → Deploy Infrastructure`); el lock de DynamoDB te bloqueará, pero no fuerces con `-lock=false`.
- Un push a `main` que toque `infra/**`, `lambdas/**` o `scripts/ec2-user-data.sh` **despliega solo** (`deploy-infra.yml`). Para pruebas, trabaja en una rama y revisa el `plan`; no hagas merge hasta estar seguro.

### Sandbox: probar cambios sin tocar producción

No necesitas otro usuario IAM: tu mismo usuario sirve. Lo que aísla la prueba es un **state distinto** y un **`project_name` distinto**.

```bash
terraform -chdir=infra init -reconfigure \
  -backend-config="bucket=aws-instances-bot-tfstate" \
  -backend-config="key=aws-instances-bot/moi-sandbox.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="dynamodb_table=aws-instances-bot-locks" \
  -backend-config="encrypt=true"

terraform -chdir=infra plan  -var="project_name=moi-test"
terraform -chdir=infra apply -var="project_name=moi-test"
# ...pruebas...
terraform -chdir=infra destroy -var="project_name=moi-test"
```

- La `key` (`moi-sandbox.tfstate`) y el `-reconfigure` son lo que te protege: con la key de producción, un `destroy` borraría el servidor real.
- Antes de cualquier `apply` o `destroy`, confirma qué state estás usando con `terraform -chdir=infra state list`: los nombres deben empezar por `moi-test`, no por `aws-instances-bot`.
- Pasa **siempre** el mismo `-var="project_name=moi-test"` en `plan`, `apply` y `destroy`. El nombre cambia los recursos, el parámetro SSM del webhook (`/discord-bot/moi-test/webhook-url`) y las reglas de EventBridge.
- El sandbox lanza **otra EC2 `m7i-flex.large`**: cuesta y puede fallar si ya hay una encendida y llegas al límite de vCPU del plan gratuito. Destrúyela al terminar.
- Para volver al state de producción, repite el `init -reconfigure` con la key `aws-instances-bot/terraform.tfstate`.

El bot de pruebas debe apuntar a la API del sandbox: toma `server_api_url` y `server_api_key` **con el state del sandbox activo**, no los de producción.

## 5. Pruebas rápidas (sin tocar infraestructura)

```bash
# Estado de la instancia
INSTANCE_ID=$(terraform -chdir=infra output -raw instance_id)
aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
  --query "Reservations[].Instances[].[InstanceId,State.Name,PublicIpAddress,InstanceType]" --output table

# Salidas de Terraform
terraform -chdir=infra output
terraform -chdir=infra output -raw server_api_url
terraform -chdir=infra output -raw server_api_key        # secreto, no lo compartas

# Probar la API de control (el mismo camino que usa el bot)
URL=$(terraform -chdir=infra output -raw server_api_url)
KEY=$(terraform -chdir=infra output -raw server_api_key)
curl -s -H "x-api-key: $KEY" "$URL/server"               # estado
curl -s -X POST -H "x-api-key: $KEY" "$URL/server/start" # encender
curl -s -X POST -H "x-api-key: $KEY" "$URL/server/stop"  # apagar

# Logs de las Lambdas
aws logs tail /aws/lambda/aws-instances-bot-server-control --follow
aws logs tail /aws/lambda/aws-instances-bot-notifier --follow
aws logs tail /aws/lambda/aws-instances-bot-auto-stop --follow
```

## 6. Probar el bot

Necesitas un `.env` propio (nunca se sube a git):

```bash
cp .env.example .env
```

| Variable | Origen |
| --- | --- |
| `DISCORD_TOKEN` | Te lo pasa el dueño del bot. Si pruebas en local, usa un bot de desarrollo aparte para no pisar la conexión del bot en producción. |
| `SERVER_API_URL` | `terraform output -raw server_api_url` |
| `SERVER_API_KEY` | `terraform output -raw server_api_key` |

```bash
npm run dev       # modo desarrollo
npm run build && npm start
```

### Bot de Discord de pruebas

Crea una aplicación aparte en el [Developer Portal](https://discord.com/developers/applications) y un servidor de Discord solo para pruebas. Así no pisas el bot de producción ni sus comandos.

| Dónde | Qué activar |
| --- | --- |
| *Bot → Privileged Gateway Intents* | Ninguno. El bot solo usa el intent `Guilds` (`src/app.ts`). |
| *OAuth2 → URL Generator → Scopes* | `bot` y `applications.commands` |
| *Bot Permissions* | `View Channels` y `Manage Webhooks` |

Con esos dos permisos el entero de permisos es `536871936`:

```text
https://discord.com/oauth2/authorize?client_id=<CLIENT_ID>&scope=bot%20applications.commands&permissions=536871936
```

- `Manage Webhooks` lo necesita `/notificaciones` para crear el webhook en el canal (`src/app/commands/notificaciones.ts`). Sin él, ese comando falla; el resto funciona.
- `/startserver`, `/stopserver` y `/status` responden por la interacción, así que no requieren `Send Messages`.
- No le des `Administrator` al bot.
- Su `.env` debe llevar `SERVER_API_URL` y `SERVER_API_KEY` **del sandbox**. Si apuntan a producción, `/stopserver` en tu servidor de pruebas apaga el servidor real.

> Dos procesos conectados con el **mismo** token de Discord interfieren entre sí. Antes de levantar el bot en local, confirma que el de producción no está usando ese token.

## 7. Costos y apagado

- La instancia `m7i-flex.large` cuesta mientras está encendida. Apágala cuando termines (`/stopserver` o `POST /server/stop`).
- AutoStop la apaga tras 30 min con CPU ≤ 5 %, pero no cuentes con eso para ahorrar.
- Revisa *Billing → Cost Explorer* de vez en cuando; con permisos de administrador puedes crear recursos que cuestan.

## 8. Qué NO hacer

- No uses ni pidas las credenciales de `Terraform-local`: tienes las tuyas.
- No subas `.env`, `*.tfvars`, access keys ni la URL del webhook de Discord.
- No edites recursos a mano en la consola si están en Terraform: el siguiente `apply` los revertirá y el `plan` mostrará drift.
- No ejecutes `terraform destroy`.

## 9. Referencias

- [`README.md`](../README.md): visión general, comandos del bot y notificaciones.
- [`docs/architecture.md`](architecture.md): diagramas y flujo de datos.
- [`docs/devops-aws.md`](devops-aws.md): CI/CD, OIDC y secretos del pipeline.
- [`docs/terraform-ec2-setup.md`](terraform-ec2-setup.md): detalle de la infraestructura en EC2.

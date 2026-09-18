# Infraestructura con AWS CDK

> **Solo referencia.** Esta carpeta es un ejemplo de como se implementaria la misma infraestructura con AWS CDK. No se despliega en este proyecto y no esta conectada a ningun pipeline de CI/CD. Terraform (`infra/*.tf`) sigue siendo la unica fuente de verdad para desplegar recursos reales. No ejecutes `cdk bootstrap`, `npm run infra:deploy` ni `npm run infra:destroy` contra la cuenta de AWS del proyecto salvo que se decida explicitamente migrar.

Esta carpeta contiene una aplicacion AWS CDK en TypeScript equivalente a la definicion Terraform.
El stack principal esta en `lib/aws-instances-stack.ts` y el entrypoint en `bin/infra.ts`.

## Que administra el stack

- VPC default y la primera subnet publica disponible.
- Security Group `aws-instances-bot-game-server`.
- Rol EC2 `aws-instances-bot-ec2-role` con `AmazonSSMManagedInstanceCore`.
- Instance profile `aws-instances-bot-ec2-profile`.
- EC2 `aws-instances-bot-game-server`.
- Rol Lambda `aws-instances-bot-automation-role` y su policy inline.
- Lambda `aws-instances-bot-auto-stop` desde `lambdas/auto_stop.py`.
- Regla EventBridge `aws-instances-bot-auto-stop` cada 15 minutos.
- Outputs de instance ID, IP publica, security group y Lambda.

## Requisitos

- Node.js 18 o superior.
- AWS CLI configurado.
- Credenciales con permisos para CDK bootstrap, CloudFormation, EC2, IAM, Lambda, EventBridge, S3 y CloudWatch Logs.
- Cuenta AWS `336425345125` y region `us-east-1`, salvo que se cambien explicitamente.

## Instalacion

Desde la raiz del repositorio:

```powershell
npm install
aws sts get-caller-identity
```

El stack toma estos valores desde `infra/cdk.json`:

| Contexto | Valor por defecto |
| --- | --- |
| `projectName` | `aws-instances-bot` |
| `instanceType` | `t3.micro` |
| `rootVolumeSizeGb` | `40` |
| `sshCidrBlocks` | `[]` |
| `autoStopEnabled` | `true` |
| `autoStopSchedule` | `rate(15 minutes)` |
| `autoStopCpuThreshold` | `5` |
| `autoStopIdleMinutes` | `30` |

No se deben poner secretos en `cdk.json`. Para cambiar valores sin modificar el archivo, usa contexto de CDK, por ejemplo:

```powershell
npx cdk synth --app "npx ts-node --project infra/tsconfig.json --prefer-ts-exts infra/bin/infra.ts" -c instanceType=t3.micro
```

## Bootstrap de CDK

CDK necesita un stack bootstrap por cuenta y region para guardar assets y ejecutar despliegues:

```powershell
npx cdk bootstrap aws://336425345125/us-east-1
```

Este comando crea recursos `CDKToolkit`, incluyendo un bucket de assets y roles de despliegue. Ejecutalo una sola vez por cuenta y region. El rol de GitHub Actions debe poder usar esos recursos.

## Validacion local

```powershell
npm run infra:synth
npm run infra:diff
```

- `infra:synth` genera CloudFormation en `cdk.out/` y no aplica cambios.
- `infra:diff` compara el template con el stack desplegado.
- El primer `synth` puede hacer lookups de la VPC default y de la AMI Ubuntu; requiere credenciales AWS de lectura.

## Migracion desde Terraform

El despliegue anterior ya creo recursos con nombres fisicos. CDK no puede adoptar automaticamente esos recursos solo por usar el mismo nombre. Hay dos rutas:

### Opcion A: importacion controlada, recomendada

1. Ejecuta `npm run infra:synth` y revisa el template.
2. Ejecuta `npm run infra:diff`.
3. Usa `cdk import AwsInstancesStack` para los recursos que ya existen y que CDK marque como importables.
4. Confirma cada recurso solicitado por CDK. Nunca uses `--force` sin revisar el diff.
5. Ejecuta nuevamente `npm run infra:diff` y confirma que no propone duplicados.
6. Despues ejecuta `npm run infra:deploy`.

La importacion debe hacerse desde una identidad con permisos de lectura y escritura sobre cada servicio. El state de Terraform en S3 no se convierte automaticamente a state de CDK; ambos sistemas mantienen estados diferentes.

### Opcion B: recursos nuevos

Solo usa esta opcion si aceptas crear recursos nuevos y retirar los anteriores de forma controlada. Cambia `projectName` o elimina primero los recursos viejos siguiendo un plan de costos y respaldo. No borres roles, Lambda, SG o EC2 manualmente si aun estan referenciados por Terraform.

## Permisos para GitHub Actions

El rol OIDC usado por el workflow debe tener, como minimo, permisos para:

- `cloudformation:*` sobre el stack de la aplicacion.
- `s3:*` sobre el bucket de assets de CDK y sus objetos.
- `iam:PassRole` sobre los roles de CloudFormation/CDK y los roles de la aplicacion.
- `ec2:*`, `lambda:*`, `events:*`, `logs:*` y las operaciones IAM que cree el stack.
- `ssm:GetParameter` para lookups de AMI cuando corresponda.

Mantén la trust policy OIDC separada de esta policy de permisos. La trust policy autoriza a GitHub a asumir el rol; la policy de permisos autoriza las operaciones de CDK.

## Deploy

Deploy local:

```powershell
npm run infra:deploy
```

El workflow `.github/workflows/deploy-infra.yml` hace lo mismo mediante GitHub Actions usando OIDC. Antes del primer deploy remoto:

1. Ejecuta `cdk bootstrap` para `us-east-1`.
2. Confirma que el rol OIDC pueda usar CloudFormation y el bucket `CDKToolkit`.
3. Revisa `npm run infra:diff`.
4. Importa recursos existentes si CDK los detecta como duplicados.
5. Ejecuta el workflow en `main`.

## Rollback y destroy

CloudFormation mantiene el historial de cambios. Para revisar un cambio antes de desplegar:

```powershell
npm run infra:diff
```

Para destruir el stack completo:

```powershell
npm run infra:destroy
```

`destroy` es destructivo y puede eliminar EC2, Lambda, security groups y roles administrados por el stack. No debe ejecutarse desde CI sin una aprobacion manual separada.

## Diferencias frente a Terraform

- Terraform usaba state remoto S3 + DynamoDB; CDK usa CloudFormation y el bootstrap `CDKToolkit`.
- `terraform plan` se reemplaza por `cdk diff`.
- `terraform apply` se reemplaza por `cdk deploy`.
- `terraform import` no se reutiliza; la adopcion se hace con `cdk import` y requiere revisar el mapeo de recursos.
- La Lambda se empaqueta como asset de CDK desde `lambdas/`.
- La AMI y la VPC se resuelven mediante context lookups de CDK.

## Riesgos conocidos

- El stack usa la VPC default y su primera subnet publica; no es una red aislada para produccion.
- Los puertos del juego estan abiertos a Internet por IPv4.
- `auto_stop.py` detiene por CPU baja; no detecta directamente jugadores conectados.
- Una migracion parcial puede dejar recursos bajo Terraform y otros bajo CDK. Durante la transicion usa un solo propietario por recurso.
- CDK bootstrap crea recursos adicionales y puede tener costo de almacenamiento minimo.

# DevOps y CI/CD para AwsInstancesBot

Este documento describe la base de despliegue recomendada para el proyecto usando GitHub Actions, Terraform y AWS.

## Objetivo

Crear un flujo de integración y despliegue seguro para:

- validar cambios del bot antes de hacer merge
- desplegar infraestructura con Terraform desde GitHub Actions
- usar AWS OIDC sin claves estáticas
- guardar el estado de Terraform en S3 con bloqueo en DynamoDB
- mantener logs y métricas en CloudWatch

## Stack recomendado

- GitHub como repositorio
- GitHub Actions para CI/CD
- Terraform para infraestructura
- Amazon S3 + DynamoDB para state remoto y locks
- IAM OIDC para autenticación de GitHub en AWS
- EC2 para el servidor de juego
- Lambda para AutoStop
- Secrets Manager para secretos del bot
- CloudWatch para observabilidad

## Requisitos previos

Antes de activar el pipeline, necesitas:

1. Un bucket S3 para el state de Terraform.
2. Una tabla DynamoDB para locks de Terraform.
3. Un rol IAM para GitHub Actions con OIDC.
4. Repositorio con ramas y entorno `production` habilitado.
5. Los secretos del repositorio configurados en GitHub.

## Secrets que se necesitan en GitHub

En Settings > Secrets and variables > Actions, añade:

- `AWS_GITHUB_OIDC_ROLE_ARN`
- `AWS_REGION`
- `TF_STATE_BUCKET`
- `TF_STATE_KEY` (opcional)
- `TF_LOCK_TABLE` (opcional)

## Crear estado remoto de Terraform

Ejemplo de recursos mínimos:

```bash
aws s3 mb s3://aws-instances-bot-tfstate --region us-east-1
aws dynamodb create-table \
  --table-name aws-instances-bot-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --region us-east-1
```

Importante:

- el bucket debe estar versionado
- la tabla DynamoDB debe activarse para locks
- activa el cifrado por defecto en S3

## Rol OIDC para GitHub Actions

El rol debe permitir que GitHub Actions asuma credenciales temporales usando OIDC.

Trust policy mínima:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:<owner>/<repo>:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

Permisos mínimos recomendados para el rol:

- `ec2:*`
- `lambda:*`
- `cloudwatch:*`
- `logs:*`
- `iam:PassRole`
- `s3:*` para el backend de Terraform
- `dynamodb:*` para los locks

En producción conviene reducirlo a lo mínimo necesario.

## Pipelines incluidos

### CI

Archivo: `.github/workflows/ci.yml`

Valida:

- instalación de dependencias
- compilación del bot con `npm run build`
- `terraform init -backend=false`
- `terraform fmt -check`
- `terraform validate`

### Deploy infraestructura

Archivo: `.github/workflows/deploy-infra.yml`

Se ejecuta en `main` o manualmente y hace:

- autenticación con AWS OIDC
- `terraform init` con backend remoto S3
- `terraform plan`
- `terraform apply`

## Siguiente paso recomendado

Después de dejar esto funcionando, el siguiente movimiento natural es:

1. desplegar la EC2 con Terraform
2. validar el Bootstrap del servidor
3. hacer despliegue del bot al EC2 o Docker
4. integrar notificaciones y CloudWatch
5. activar alertas de gasto y alertas de salud

## Riesgos a tener en cuenta

- no crear recursos con `apply` sin revisar el plan
- no usar `AdministratorAccess` en el rol de GitHub Actions
- no dejar secretos en el repo
- no hacer `destroy` desde CI sin gate explícito
- revisar costos de EC2 y Lambda antes de producción

## Estado

Esto es la base de DevOps para empezar a subir despliegues reales con seguridad y reproducibilidad.

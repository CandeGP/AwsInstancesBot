# Configuracion de EC2 con Terraform

Este documento explica la infraestructura creada para el proyecto `AwsInstancesBot`, como instalar las herramientas necesarias, como configurar el acceso a AWS, que recursos administra Terraform y como crear, probar, detener o eliminar la instancia.

## 1. Objetivo

La configuracion de Terraform prepara una instancia EC2 para alojar el servidor de juego, inicialmente Project Zomboid. Tambien crea los recursos basicos necesarios para administrarla:

- Una instancia EC2 con Ubuntu.
- Un grupo de seguridad para el servidor.
- Un rol IAM para administrar la instancia mediante Systems Manager.
- Un perfil de instancia IAM asociado a la EC2.
- Un script `user_data` ejecutado durante el primer arranque.
- Outputs para consultar el ID, la IP publica y el grupo de seguridad.

Terraform permite describir estos recursos como codigo. En lugar de crear cada recurso manualmente desde la consola de AWS, Terraform usa la API de AWS para crearlos y mantener su estado.

> Esta configuracion todavia no instala Project Zomboid. El script de instalacion se agregara despues de validar los comandos oficiales para Linux.

## 2. Estructura utilizada

```text
AwsInstancesBot/
├── infra/
│   ├── main.tf                    # Proveedor, datos y recursos AWS
│   ├── variables.tf               # Variables y valores predeterminados
│   ├── outputs.tf                 # Valores mostrados despues del despliegue
│   └── terraform.tfvars.example   # Ejemplo de valores personalizados
├── scripts/
│   └── ec2-user-data.sh           # Script de arranque de la EC2
└── docs/
    └── terraform-ec2-setup.md     # Este documento
```

Terraform tambien crea localmente archivos que no deben subirse al repositorio:

```text
infra/.terraform/       # Provider descargado
infra/terraform.tfstate # Estado real de los recursos
infra/*.tfstate.*       # Backups o estados adicionales
```

El `.gitignore` del proyecto ya excluye estos archivos de estado y la carpeta `.terraform`.

## 3. Requisitos previos

Antes de crear recursos se necesita:

- Una cuenta de AWS activa.
- Un metodo de pago configurado en AWS.
- Terraform 1.6 o superior.
- AWS CLI.
- Un usuario IAM o una identidad equivalente con permisos para la infraestructura.
- PowerShell abierto despues de instalar las herramientas para que el `PATH` se actualice.

La cuenta de AWS es necesaria aunque Terraform automatice el proceso. Terraform no elimina la necesidad de una cuenta ni de credenciales; solamente evita crear los recursos manualmente.

## 4. Instalar Terraform en Windows

Descarga Terraform desde la pagina oficial:

<https://developer.hashicorp.com/terraform/install>

Instala la version para Windows y verifica que el ejecutable este disponible:

```powershell
terraform version
```

Debe mostrar una version igual o superior a `1.6.0`, porque esa es la version minima declarada en `infra/main.tf`.

Si PowerShell no reconoce `terraform` despues de instalarlo:

1. Cierra todas las terminales abiertas.
2. Abre una nueva terminal.
3. Ejecuta de nuevo `terraform version`.
4. Comprueba que la carpeta donde esta `terraform.exe` aparezca en `PATH`.

## 5. Instalar AWS CLI

En Windows puede instalarse AWS CLI desde:

<https://aws.amazon.com/cli/>

Tambien puede instalarse mediante Chocolatey si Chocolatey esta disponible:

```powershell
choco install awscli
```

Comprueba la instalacion:

```powershell
aws --version
```

Si AWS CLI esta instalado pero la terminal aun no reconoce el comando, una ruta habitual es:

```text
C:\Program Files\Amazon\AWSCLIV2\aws.exe
```

En ese caso puede ejecutarse temporalmente con la ruta completa:

```powershell
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" --version
```

## 6. Crear credenciales para Terraform

Terraform necesita autenticarse contra AWS. Para desarrollo local se puede usar un usuario IAM dedicado, por ejemplo `terraform-local`.

En AWS:

1. Abre **IAM**.
2. Ve a **Users**.
3. Crea un usuario llamado `terraform-local`.
4. Entra en **Security credentials**.
5. Crea una access key para uso desde la CLI.
6. Guarda el `Access key ID` y el `Secret access key`.

La clave secreta solo se muestra una vez. No debe enviarse por Discord, pegarse en GitHub ni escribirse en archivos del proyecto.

Configura las credenciales desde PowerShell:

```powershell
aws configure
```

Valores orientativos:

```text
AWS Access Key ID: AKIA...
AWS Secret Access Key: ...
Default region name: us-east-1
Default output format: json
```

AWS CLI guardara la configuracion en el perfil local del usuario, normalmente:

```text
C:\Users\<usuario>\.aws\credentials
C:\Users\<usuario>\.aws\config
```

Comprueba la identidad sin revelar la clave secreta:

```powershell
aws sts get-caller-identity
```

Si el comando devuelve el `Account`, `UserId` y `Arn`, las credenciales funcionan.

### Permisos del usuario de Terraform

Para una prueba inicial, el usuario debe poder consultar VPC, subredes y AMIs, crear la EC2 y el grupo de seguridad, y crear el rol IAM que utiliza la instancia.

La politica debe incluir como minimo permisos equivalentes a:

- AmazonEC2FullAccess
- IAMFullAccess

No se recomienda usar `AdministratorAccess` como solucion permanente. Para un entorno real conviene crear una politica limitada a los recursos y acciones que Terraform necesita.

La politica `AmazonSSMManagedInstanceCore` no se asigna al usuario local de Terraform. Esa politica se asigna al rol de la EC2 en `main.tf`, para que la instancia pueda registrarse en Systems Manager.

## 7. Configuracion de variables

### `infra/variables.tf`

Define las variables que utiliza la infraestructura:

| Variable | Valor actual | Funcion |
| --- | --- | --- |
| `aws_region` | `us-east-1` | Region donde se crean los recursos |
| `project_name` | `aws-instances-bot` | Prefijo para nombres y tags |
| `instance_type` | `t3.micro` | Tipo de instancia EC2 por defecto |
| `root_volume_size_gb` | `20` | Tamano del disco raiz |
| `ssh_cidr_blocks` | `[]` | Redes autorizadas para SSH |

`ssh_cidr_blocks` esta vacia intencionalmente. Eso significa que SSH no se abre por defecto. Si se necesitara acceso SSH temporal, se debe usar una IP concreta, por ejemplo:

```hcl
ssh_cidr_blocks = ["203.0.113.10/32"]
```

No se debe usar `0.0.0.0/0` para SSH en una configuracion real.

### Diferencia con `terraform.tfvars.example`

El archivo de ejemplo actualmente contiene:

```hcl
instance_type       = "m5.large"
root_volume_size_gb = 30
```

Mientras que `variables.tf` tiene por defecto:

```hcl
instance_type       = "t3.micro"
root_volume_size_gb = 20
```

Si no se proporciona un archivo `.tfvars`, Terraform usa los valores de `variables.tf`. Si se copia el archivo de ejemplo a `terraform.tfvars`, los valores del ejemplo tendran prioridad.

Por tanto, antes de ejecutar `apply`, hay que elegir conscientemente una configuracion. `m5.large` no es Free Tier y puede generar costos desde el primer momento. Para pruebas iniciales se recomienda mantener `t3.micro` o elegir otro tipo compatible con el presupuesto y la arquitectura del juego.

## 8. Recursos creados en `main.tf`

### 8.1 Proveedor AWS

```hcl
provider "aws" {
  region = var.aws_region
}
```

Indica a Terraform que debe usar AWS y que la region se obtiene de la variable `aws_region`.

### 8.2 VPC y subred

```hcl
data "aws_vpc" "default" {
  default = true
}
```

Terraform no crea una VPC nueva en esta primera version. Busca la VPC por defecto de la cuenta.

Tambien busca las subredes de esa VPC y utiliza la primera:

```hcl
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}
```

Esto simplifica el primer despliegue, pero para produccion conviene crear una VPC propia con subredes y reglas de red controladas por Terraform.

### 8.3 AMI Ubuntu

La configuracion busca la AMI mas reciente de Ubuntu 24.04 LTS para x86_64:

```hcl
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
}
```

La AMI depende de la region. Si no existe una AMI que coincida en la region elegida, el plan fallara y habra que ajustar el filtro.

### 8.4 Grupo de seguridad

El recurso `aws_security_group.game_server` controla el trafico de red de la EC2.

Reglas de entrada actuales:

| Puerto | Protocolo | Uso |
| --- | --- | --- |
| `22` | TCP | SSH, solo si se agrega una red a `ssh_cidr_blocks` |
| `16261` | UDP | Puerto principal de Project Zomboid |
| `16262-16272` | TCP | Rango inicial de jugadores definido para el servidor |

La salida permite trafico hacia cualquier destino para que Ubuntu pueda actualizarse y el servidor pueda descargar dependencias.

Los puertos de Project Zomboid deben confirmarse contra la documentacion de la version del juego que se vaya a instalar. Si la documentacion indica puertos distintos, se actualiza el grupo de seguridad antes de desplegar.

### 8.5 Rol IAM de la instancia

`aws_iam_role.ec2` permite que EC2 asuma un rol de AWS:

```hcl
Principal = {
  Service = "ec2.amazonaws.com"
}
```

El rol se adjunta a un instance profile y se utiliza por la instancia. No contiene permisos generales de administrador.

### 8.6 Politica de Systems Manager

Se asocia la politica administrada:

```text
arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
```

Esto permite administrar la EC2 mediante AWS Systems Manager, evitando abrir SSH publicamente. Para que funcione, la instancia tambien necesita conectividad de salida a los servicios de AWS.

### 8.7 Instance profile

`aws_iam_instance_profile.ec2` conecta el rol IAM con la instancia EC2. Una instancia no recibe directamente un rol; recibe un instance profile que contiene el rol.

### 8.8 Instancia EC2

El recurso `aws_instance.game_server` crea la maquina con:

- AMI Ubuntu seleccionada automaticamente.
- Tipo definido por `instance_type`.
- Primera subred de la VPC por defecto.
- Grupo de seguridad del servidor.
- IP publica asociada.
- Instance profile para Systems Manager.
- Script `scripts/ec2-user-data.sh`.

El disco raiz usa:

- Tipo `gp3`.
- Tamano definido por `root_volume_size_gb`.
- Cifrado activado.
- Eliminacion al terminar la instancia.

La etiqueta `Name` y las etiquetas `Project` y `Role` ayudan a identificar el recurso en AWS.

## 9. Script `user_data`

El archivo `scripts/ec2-user-data.sh` se ejecuta durante el primer arranque de la EC2. Actualmente realiza estas tareas:

1. Activa el modo de error del shell con `set -euo pipefail`.
2. Guarda la salida en:

   ```text
   /var/log/aws-instances-bot-bootstrap.log
   ```

3. Actualiza los paquetes de Ubuntu.
4. Instala `ca-certificates`, `curl` y `unzip`.
5. Crea `/opt/aws-instances-bot`.
6. Escribe un archivo de confirmacion del bootstrap.
7. Intenta activar `amazon-ssm-agent`.

Todavia no instala Project Zomboid. Cuando se tenga una guia validada, los comandos pueden agregarse a este archivo. Es recomendable probar primero la instalacion manualmente en una EC2 temporal antes de ponerla en `user_data`.

El script se ejecuta principalmente al crear la instancia. Modificarlo despues no necesariamente vuelve a ejecutarlo sobre una instancia existente; normalmente se necesita reemplazar la instancia, ejecutar una nueva provision o aplicar el cambio manualmente mediante Systems Manager.

## 10. Inicializar Terraform

Desde PowerShell:

```powershell
cd C:\Users\{USER}\AwsInstancesBot\infra
terraform init
```

Este comando:

- Descarga el provider de AWS.
- Crea `.terraform/`.
- Prepara el directorio para planificar y aplicar.

No crea recursos en AWS.

## 11. Validar la configuracion

Ejecuta:

```powershell
terraform fmt -check
terraform validate
```

`terraform fmt -check` revisa el formato. `terraform validate` revisa la estructura y tipos de la configuracion, pero no confirma que AWS permita crear los recursos.

Para formatear automaticamente los archivos:

```powershell
terraform fmt
```

## 12. Revisar el plan

Antes de crear recursos:

```powershell
terraform plan
```

Terraform consultara AWS para comprobar la VPC, las subredes y la AMI, y mostrara el cambio previsto.

El plan debe revisarse para confirmar:

- Region correcta.
- Tipo de instancia esperado.
- Tamano de disco esperado.
- Puertos publicados esperados.
- Ninguna regla SSH abierta accidentalmente.
- Ningun recurso inesperado.

Tambien se puede guardar el plan:

```powershell
terraform plan -out=tfplan
```

Y aplicarlo exactamente despues:

```powershell
terraform apply tfplan
```

## 13. Crear la instancia

Si el plan es correcto, ejecutar:

```powershell
terraform apply
```

Terraform pedira confirmacion. Escribe `yes` solo despues de revisar el resumen.

El comando crea los recursos en este orden logico:

1. VPC y subred se consultan, no se crean.
2. Grupo de seguridad.
3. Rol IAM.
4. Politica asociada al rol.
5. Instance profile.
6. Instancia EC2.
7. Script de bootstrap durante el arranque.

La EC2 normalmente se crea encendida. `terraform apply` no es una simulacion y puede generar costos.

## 14. Consultar outputs

Al finalizar:

```powershell
terraform output
```

Outputs disponibles:

### `instance_id`

Identificador de la EC2. Se usa para consultar o detener la instancia.

```powershell
terraform output -raw instance_id
```

### `instance_public_ip`

IP publica actual de la instancia.

```powershell
terraform output -raw instance_public_ip
```

Una IP publica puede cambiar si la instancia se detiene y vuelve a iniciar, salvo que se utilice una Elastic IP.

### `security_group_id`

Identificador del grupo de seguridad asociado.

```powershell
terraform output -raw security_group_id
```

## 15. Comprobar el estado de la EC2

Con AWS CLI:

```powershell
$instanceId = terraform output -raw instance_id
aws ec2 describe-instances `
  --instance-ids $instanceId `
  --region us-east-1 `
  --query "Reservations[0].Instances[0].State.Name" `
  --output text
```

El resultado esperado despues de arrancar es:

```text
running
```

Para comprobar que Systems Manager la reconoce:

```powershell
aws ssm describe-instance-information `
  --region us-east-1 `
  --output table
```

Puede tardar algunos minutos despues del primer arranque.

## 16. Revisar el bootstrap

El log se encuentra dentro de la EC2:

```text
/var/log/aws-instances-bot-bootstrap.log
```

Se puede consultar mediante Session Manager cuando la instancia aparezca como administrada. Si se habilita SSH de forma temporal y segura, tambien puede consultarse con:

```bash
sudo cat /var/log/aws-instances-bot-bootstrap.log
```

La consola de EC2 tambien muestra el output inicial de `user_data` en la opcion de logs de la instancia.

## 17. Detener la instancia durante las pausas

Para detenerla sin eliminarla:

```powershell
$instanceId = terraform output -raw instance_id
aws ec2 stop-instances `
  --instance-ids $instanceId `
  --region us-east-1
```

Al detenerla se conserva el disco y la configuracion. Sin embargo, pueden continuar algunos costos:

- Volumen EBS.
- Direccion IPv4 publica, segun el tipo y la politica vigente de AWS.
- Snapshots u otros recursos adicionales.

Para volver a iniciarla:

```powershell
aws ec2 start-instances `
  --instance-ids $instanceId `
  --region us-east-1
```

## 18. Eliminar todos los recursos

Cuando no se necesite conservar la infraestructura:

```powershell
terraform destroy
```

Revisa el resumen y escribe `yes` solo si quieres eliminar los recursos administrados por esta configuracion.

`terraform destroy` elimina la EC2, el grupo de seguridad, el rol, el instance profile y los recursos asociados que Terraform tenga en su estado. El estado local no es una copia de seguridad del servidor; los datos importantes del juego deben respaldarse aparte.

## 19. Costos y Free Tier

Un `m5.large` no es una instancia Free Tier y puede ser rechazada en cuentas que solo permiten tipos elegibles para Free Tier. Ademas, genera costos mientras permanece encendida.

Para pruebas iniciales, el valor actual de `variables.tf` es `t3.micro`, pero la disponibilidad y elegibilidad dependen de la cuenta, region y fecha. No se debe asumir que cualquier cuenta tiene exactamente las mismas condiciones.

Buenas practicas:

- Ejecutar `terraform plan` antes de `apply`.
- Mantener la instancia detenida cuando no se usa.
- Ejecutar `terraform destroy` si no se trabajara durante varios dias.
- Crear un AWS Budget y alertas de costo.
- Revisar EBS, IPs publicas y snapshots.
- No dejar recursos de prueba olvidados.

## 20. Seguridad

No guardar en el repositorio:

- Access keys.
- Secret access keys.
- Tokens de Discord.
- Archivos `.env`.
- `terraform.tfstate`.
- Archivos `.tfvars` con datos privados.

La configuracion actual aplica algunas medidas:

- Disco raiz cifrado.
- SSH cerrado por defecto.
- Rol IAM especifico para Systems Manager.
- Sin credenciales escritas en los `.tf`.

Antes de produccion conviene mejorar:

- Usar una VPC propia.
- Limitar reglas a CIDR y puertos exactos.
- Usar un backend remoto cifrado para el estado Terraform, por ejemplo S3 con locking.
- Separar cuentas o entornos de desarrollo y produccion.
- Usar roles temporales o IAM Identity Center en lugar de access keys permanentes.
- Agregar CloudWatch, backups y alertas.

## 21. Problemas comunes

### `No valid credential sources found`

AWS CLI o Terraform no encuentran credenciales. Ejecuta:

```powershell
aws configure
aws sts get-caller-identity
```

### `The specified instance type is not eligible for Free Tier`

El tipo seleccionado no es elegible para Free Tier. Usa temporalmente el tipo definido en `variables.tf`, revisa tu presupuesto o habilita una cuenta con facturacion configurada.

### No existe la AMI Ubuntu

La AMI se busca por nombre y region. Comprueba la region y ajusta el filtro de AMI si es necesario.

### La instancia no aparece en Systems Manager

Espera unos minutos y confirma que:

- El instance profile esta asociado.
- La politica `AmazonSSMManagedInstanceCore` esta adjunta.
- La instancia tiene salida a Internet o endpoints VPC apropiados.
- El agente SSM esta instalado y activo.

### El script no termina correctamente

Consulta:

```text
/var/log/aws-instances-bot-bootstrap.log
```

Un error en `user_data` no siempre provoca que Terraform falle, porque Terraform puede terminar de crear la EC2 aunque un comando interno del script haya fallado.

## 22. Secuencia recomendada para el proyecto

Para esta etapa de desarrollo:

```powershell
cd C:\Users\{USERS}\AwsInstancesBot\infra
terraform init
terraform plan
terraform apply
terraform output
# probar la instancia y el bootstrap
aws ec2 stop-instances --instance-ids TU_INSTANCE_ID --region us-east-1
```

Cuando se agregue la instalacion de Project Zomboid:

1. Validar el script manualmente en Ubuntu.
2. Actualizar `scripts/ec2-user-data.sh`.
3. Ejecutar `terraform plan`.
4. Crear una instancia de prueba o reemplazar la existente conscientemente.
5. Revisar el log de bootstrap.
6. Probar los puertos del servidor.
7. Implementar AutoStop y AutoStart con Lambda y CloudWatch.
8. Integrar el bot de Discord con las operaciones de EC2.

Esta configuracion es la base de la Fase 2. Todavia no implementa AutoStop, AutoStart, CloudWatch, Lambda ni la instalacion automatica de Project Zomboid.

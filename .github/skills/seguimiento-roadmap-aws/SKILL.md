---
name: seguimiento-roadmap-aws
description: "Analiza el avance de AwsInstancesBot contra README.md, toda la documentacion de docs/ y el roadmap; verifica el estado real en codigo e infraestructura, detecta diferencias, propone el siguiente paso priorizado, aplica mejoras pequenas y documenta cada cambio. Usar para revisiones de progreso, planificacion tecnica, mejora continua, comparacion de fases, AWS, Terraform, Lambda, EC2 o bot de Discord."
argument-hint: "Indica el objetivo, fase o area que quieres revisar"
user-invocable: true
---

# Seguimiento del roadmap de AwsInstancesBot

## Objetivo

Producir una revision de avance reproducible y accionable del proyecto. La revision debe distinguir entre lo que esta documentado, lo que existe en el repositorio y lo que esta validado por comandos o pruebas. Nunca marques una capacidad como terminada solo porque aparece en `README.md` o en el roadmap.

## Cuando usar esta skill

- Revisar el avance general del proyecto.
- Comparar una fase del roadmap con la implementacion actual.
- Elegir el siguiente paso de desarrollo.
- Proponer mejoras incrementales de seguridad, calidad, costos, pruebas o documentacion.
- Verificar cambios en Terraform, EC2, Lambda, EventBridge, CloudWatch o el bot de Discord.
- Documentar que se aplico y que quedo pendiente.

## Procedimiento

### 1. Definir el alcance

1. Identifica el objetivo indicado por el usuario: proyecto completo, fase, componente o problema.
2. Si no hay un alcance claro, usa la revision completa y declara esa suposicion.
3. No cambies archivos durante esta etapa de lectura.

### 2. Leer la fuente de verdad documental

Lee completamente, cuando existan:

- `README.md`.
- Todos los archivos de texto dentro de `docs/`, especialmente `docs/generalRoadmap.md`, `docs/requirements.md`, `docs/architecture.md` y las guias operativas.
- `package.json`, `tsconfig.json` y configuraciones de CI/CD.

Extrae una matriz con: requisito o entregable, fase, evidencia esperada, estado documental y riesgos o decisiones pendientes. Incluye las contradicciones entre documentos en una lista separada.

### 3. Comprobar el estado real del repositorio

Inspecciona solo los archivos necesarios para confirmar cada afirmacion:

- `src/` para comandos, eventos, integraciones, permisos y manejo de errores.
- `infra/` para recursos Terraform, variables, outputs, IAM, red, tags, eventos y defaults.
- `lambdas/` para handlers, metricas, ventanas de tiempo y acciones sobre AWS.
- `scripts/` para despliegue, destruccion y bootstrap.
- Pruebas, workflows, Docker y archivos de configuracion si el roadmap los menciona.

Busca evidencia concreta: simbolo, recurso, archivo, comando, test o salida de validacion. Clasifica cada punto como:

- `Implementado y validado`: existe y una comprobacion lo respalda.
- `Implementado sin validar`: existe, pero falta una prueba, plan, despliegue controlado o evidencia operacional.
- `Parcial`: solo cubre una parte del requisito.
- `Documentado solamente`: aparece en documentos, pero no hay implementacion.
- `Pendiente`: no hay evidencia suficiente.
- `Bloqueado`: depende de una decision, credencial, servicio o dato externo.

### 4. Ejecutar la comprobacion mas barata que discrimine

Antes de proponer trabajo, elige una comprobacion local y segura que pueda refutar la hipotesis principal:

- TypeScript: `npm run build`.
- Terraform: desde `infra/`, `terraform fmt -check` y `terraform validate`.
- Scripts: inspeccion estatica y ejecucion solo de rutas no destructivas.
- Lambda: prueba local del handler si existen dependencias y fixtures.
- Documentacion: comprobar que rutas, comandos y nombres de recursos mencionados existen.

No ejecutes `terraform apply`, `terraform destroy`, cambios en AWS ni acciones con costo sin confirmacion explicita. Nunca expongas tokens, claves, `.env`, `terraform.tfstate` ni valores sensibles.

### 5. Comparar contra el roadmap

Presenta una tabla breve con estas columnas:

| Fase o entregable | Evidencia actual | Estado | Faltante principal | Riesgo o dependencia |
| --- | --- | --- | --- | --- |

Compara el orden previsto con las dependencias reales. Prioriza primero lo que desbloquea otras capacidades o evita riesgo de costo, seguridad o perdida de datos. Señala si el repositorio avanzo de fase sin cerrar criterios de la fase anterior.

Para este repositorio, revalida especialmente estas areas en cada revision:

- El bot actualmente tiene un comando `/status`; no asumas que los comandos de gestion de EC2 ya existen.
- Terraform y el bootstrap de EC2 deben contrastarse con la instalacion real de Project Zomboid.
- AutoStop basado en CPU no equivale a detectar jugadores; debe tratarse como aproximacion temporal.
- La configuracion efectiva de `auto_stop_enabled` debe compararse con lo que afirma la documentacion.
- Las decisiones DynamoDB/RDS, `userData`/AMI y plataforma de ejecucion siguen siendo decisiones hasta que exista una eleccion implementada y documentada.
- README puede mencionar Docker, CI/CD, Fargate o dashboard aunque esos archivos no esten presentes; verifica cada uno.

### 6. Proponer el siguiente paso

Propone un solo siguiente paso principal, pequeno y verificable. Debe incluir:

1. Resultado esperado.
2. Archivos o componentes que se tocaran.
3. Dependencias y riesgos.
4. Criterio de aceptacion observable.
5. Comando o prueba que lo valida.
6. Alternativa si existe un bloqueo real.

Despues, incluye de dos a cuatro mejoras continuas ordenadas por impacto y esfuerzo. Usa ejemplos concretos, por ejemplo: pruebas del handler de AutoStop con mocks, validacion de permisos IAM, `terraform plan` controlado, contrato de estado entre bot y EC2, metricas reales de jugadores, alertas de presupuesto, o un registro de decisiones ADR.

### 7. Aplicar cambios, solo si el usuario los solicita o el objetivo lo implica

Haz el cambio minimo que permita avanzar. Conserva APIs y estilo existentes. Antes de editar, declara una hipotesis falsable y el chequeo que podria refutarla. Tras la primera edicion, ejecuta inmediatamente la validacion mas estrecha disponible y repara el mismo slice si falla.

No mezcles refactors no relacionados. Para infraestructura, favorece cambios reversibles y no destructivos. Para permisos, usa el menor alcance posible. Para configuracion con costo, deja defaults seguros y explica cualquier activacion.

### 8. Documentar cada aplicacion

Despues de cualquier cambio, actualiza la documentacion relevante y registra:

- Fecha o contexto de la revision.
- Problema u oportunidad detectada.
- Estado anterior y estado nuevo.
- Archivos modificados.
- Comandos y resultados de validacion.
- Riesgos, decisiones pendientes y proximo criterio de aceptacion.

Usa la documentacion existente cuando corresponda. Si falta un lugar para el historial, crea o propone `docs/progress-log.md` antes de inventar otra ubicacion. No declares una tarea completa si solo se actualizo la documentacion.

## Formato de salida

Responde en espanol y con esta estructura:

### Estado actual
Una frase con la fase real y el nivel de confianza.

### Evidencia y diferencias
- Hechos verificados con rutas de archivos.
- Contradicciones entre codigo, configuracion y documentacion.
- Validaciones ejecutadas y su resultado.

### Comparacion con el roadmap
Tabla de fases o entregables, estado y faltantes.

### Siguiente paso recomendado
Un unico paso principal con criterio de aceptacion y comando de validacion.

### Mejora continua
De dos a cuatro propuestas pequenas, priorizadas por impacto y esfuerzo.

### Cambios aplicados y documentacion
Solo si hubo ediciones: archivos, resumen del cambio, pruebas ejecutadas y registro documental actualizado. Si no hubo ediciones, indica que la revision fue solo diagnostica.

## Criterios de calidad

- Toda conclusion importante tiene evidencia local o esta marcada como supuesto.
- README, `docs/` y codigo se comparan; ninguno sustituye a los otros.
- El siguiente paso es concreto, acotado y comprobable.
- Se distinguen implementacion, validacion y despliegue.
- Se consideran seguridad, costos, permisos, datos y reversibilidad.
- No se ejecutan acciones destructivas o con costo sin autorizacion.
- Cada cambio aplicado queda reflejado en la documentacion y sus pruebas.

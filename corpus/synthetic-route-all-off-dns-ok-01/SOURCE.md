# synthetic-route-all-off-dns-ok-01

Caso sintetico propio. Enrutamiento de aplicacion apagado pero el nombre resuelve a la IP privada del endpoint (trafico RFC1918 entra a la VNet): sin falla detectada.

Fuente de la regla: https://learn.microsoft.com/en-us/azure/app-service/configure-vnet-integration-routing

## Naturaleza del caso

Es un caso de regresion propio: fija lo que este prototipo debe concluir ante un snapshot sintetico que escribimos nosotros. No es verdad de Azure ni salida real de Azure; la fuente solo respalda la regla, no el resultado esperado.

Tipo: synthetic
Fecha de lectura: 2026-11-19
Reviso: pendiente

# synthetic-route-all-off-01

Caso sintetico propio. Enrutamiento de aplicacion apagado (outboundVnetRouting.allTraffic=false) y el nombre no resuelve a IP privada: origin ambar, dns rojo.

Fuente de la regla: https://learn.microsoft.com/en-us/azure/app-service/configure-vnet-integration-routing

## Naturaleza del caso

Es un caso de regresion propio: fija lo que este prototipo debe concluir ante un snapshot sintetico que escribimos nosotros. No es verdad de Azure ni salida real de Azure; la fuente solo respalda la regla, no el resultado esperado.

Tipo: synthetic
Fecha de lectura: 2026-11-19
Reviso: pendiente

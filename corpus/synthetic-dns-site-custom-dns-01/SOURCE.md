# synthetic-dns-site-custom-dns-01

Caso sintetico propio. El sitio define dnsConfiguration.dnsServers (anula el DNS de la VNet): la cadena no se puede evaluar, ambar aunque la zona no este enlazada.

Fuente de la regla: https://learn.microsoft.com/en-us/azure/app-service/overview-name-resolution

## Naturaleza del caso

Es un caso de regresion propio: fija lo que este prototipo debe concluir ante un snapshot sintetico que escribimos nosotros. No es verdad de Azure ni salida real de Azure; la fuente solo respalda la regla, no el resultado esperado.

Tipo: synthetic
Fecha de lectura: 2026-11-19
Reviso: pendiente

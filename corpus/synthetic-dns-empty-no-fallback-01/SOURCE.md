# synthetic-dns-empty-no-fallback-01

Caso sintetico propio. Zona privatelink enlazada a la VNet de integracion pero sin registros, y el link con resolutionPolicy Default: NXDOMAIN.

Fuente de la regla: https://learn.microsoft.com/en-us/azure/dns/private-dns-fallback

## Naturaleza del caso

Es un caso de regresion propio: fija lo que este prototipo debe concluir ante un snapshot sintetico que escribimos nosotros. No es verdad de Azure ni salida real de Azure; la fuente solo respalda la regla, no el resultado esperado.

Tipo: synthetic
Fecha de lectura: 2026-11-19
Reviso: pendiente

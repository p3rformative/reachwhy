# synthetic-dns-fallback-01

Caso sintetico propio. Misma zona sin registros, pero el link tiene resolutionPolicy NxDomainRedirect: la consulta cae a resolucion publica (ambar).

Fuente de la regla: https://learn.microsoft.com/en-us/azure/dns/private-dns-fallback

## Naturaleza del caso

Es un caso de regresion propio: fija lo que este prototipo debe concluir ante un snapshot sintetico que escribimos nosotros. No es verdad de Azure ni salida real de Azure; la fuente solo respalda la regla, no el resultado esperado.

Tipo: synthetic
Fecha de lectura: 2026-11-19
Reviso: pendiente

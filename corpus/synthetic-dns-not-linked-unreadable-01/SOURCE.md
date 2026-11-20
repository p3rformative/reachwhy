# synthetic-dns-not-linked-unreadable-01

Caso sintetico propio. La zona del snapshot no esta enlazada a la VNet de integracion, pero la suscripcion hub no es legible: puede existir otra zona con el mismo nombre enlazada alli, asi que es ambar, nunca rojo.

Fuente de la regla: https://learn.microsoft.com/en-us/azure/dns/private-dns-arg

## Naturaleza del caso

Es un caso de regresion propio: fija lo que este prototipo debe concluir ante un snapshot sintetico que escribimos nosotros. No es verdad de Azure ni salida real de Azure; la fuente solo respalda la regla, no el resultado esperado.

Tipo: synthetic
Fecha de lectura: 2026-11-19
Reviso: pendiente

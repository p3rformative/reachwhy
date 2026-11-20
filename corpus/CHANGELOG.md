# Changelog del corpus

- 1.0.0: caso inicial `demo-basic-01` (sintetico).
- 1.0.0 (2026-11-19): 8 casos sinteticos de la fase 1: `synthetic-dns-empty-no-fallback-01`, `synthetic-dns-fallback-01`, `synthetic-dns-hub-zone-01`, `synthetic-dns-hub-not-visible-01`, `synthetic-dns-zone-missing-01`, `synthetic-dns-site-custom-dns-01`, `synthetic-route-all-off-01`, `synthetic-route-all-off-dns-ok-01`. Sin cambios de esquema; `overall` de estos casos cubre solo los saltos evaluados (origin, dns).
- 1.0.0 (2026-11-19, revision): `synthetic-dns-not-linked-unreadable-01` y `synthetic-dns-visibility-undeclared-01` (zona ausente o sin link con ambito no legible o visibilidad sin declarar: ambar `DNS_ZONE_NOT_VISIBLE`, nunca rojo). `overall` de `synthetic-dns-hub-zone-01` y `synthetic-route-all-off-dns-ok-01` pasa de green a amber: el motor es parcial y no puede dar green. Todos los `SOURCE.md` aclaran que son casos de regresion propios, no verdad de Azure. Sin cambios de esquema.

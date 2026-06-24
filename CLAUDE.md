# Instrucciones del proyecto — Austral Breathing

## Idioma
- **Responder SIEMPRE en español.** Toda la comunicación con el usuario debe ser
  en español, sin excepción.

## Git y autoría
- **No crear ramas que aludan a Claude, IA, bot o similares.** Usar nombres de
  rama descriptivos del trabajo (p. ej. `phase2-outreach`).
- **Todos los commits deben quedar firmados como autoría del usuario**
  (Guillermo Servando Fuentes Jaque). No firmar como Claude ni añadir
  co-autores/trailers de Claude/Anthropic.
- No incluir identificadores de modelo ni menciones a Claude/IA en commits, PRs,
  comentarios de código ni ningún artefacto versionado.

## Entorno
- El `git push` directo solo funciona a la rama de sesión preautorizada; para
  otras ramas, empujar igualmente vía el remoto si el proxy lo permite, o usar la
  API de GitHub (`create_branch`/`push_files`) y dejar que los workflows
  regeneren los derivados.
- Hosts de datos (AmeriFlux/ORNL/FLUXNET/WorldClim) y `api.github.com` pueden
  estar bloqueados por egress. Resolver con workflows fetch-proxy en runners de
  Actions (internet abierto), no asumir acceso directo desde el entorno.

## Validación antes de abrir PR
- `python3 scripts_verify_registry.py` debe dar **ERROR=0**.
- `python3 -m pytest -q` debe pasar.
- Abrir el PR como **draft**.

# Security policy

## Reporting a vulnerability

Do not open a public issue containing credentials, exploit details, private chat data, or device/network identifiers. Contact the repository owner privately and include the affected revision, impact, and a minimal reproduction with all secrets redacted.

## Secrets and local data

`config.yaml`, `db.json`, and `iot_code/private_const.py` are local-only files. Never commit them or include their values in logs, screenshots, fixtures, or bug reports. Use long random values for `telegram.api_token` and `iot.shared_secret`, restrict file permissions, and rotate credentials immediately if they may have been exposed.

Generate firmware constants with `make sync-config`: it replaces the destination atomically with permissions `0600` and reports key names only. Run `make sync-config-dry-run` first when checking a new configuration or target.

Secrets stored on a MicroPython board may be recoverable by someone with physical access. Use a dedicated, restricted Wi-Fi network where possible and keep device credentials independently rotatable.

## Deployment baseline

- Do not expose the development server directly to the public internet.
- Put public deployments behind a maintained HTTPS reverse proxy or private tunnel.
- Restrict inbound access with a firewall and authenticate every data-reading endpoint.
- Keep the container and Python dependencies updated from trusted sources.
- Back up the persistent database volume before upgrades.
- Review logs for accidental credential disclosure before sharing them.

The sensor API authenticates reads and writes using the configured shared secret. Prefer the `Authorization: Bearer` header; JSON-body authentication remains supported for existing firmware. Failed authentication never logs the submitted credential. HTTPS is required outside a trusted private network because a captured credential can still be replayed.

The application enforces a small request-body limit, a configurable water-level range, and a basic per-client rate limit. Internet-facing deployments should also enforce limits at the reverse proxy or firewall.

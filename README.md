# Elering Estfeed — Consumer Meter Data API

A guide and Python script for fetching your own electricity meter data from the Estonian Estfeed Datahub.

## Background

Elering operates two portals:

| Portal | URL | For |
|--------|-----|-----|
| Customer portal | https://estfeed.elering.ee | Regular consumers — view your own data |
| Market participant datahub | https://datahub.elering.ee | Grid operators, suppliers (requires formal contract) |

As a regular consumer, authentication goes through Estonian national identity (Smart-ID / Mobile-ID / ID card) via TARA → Keycloak (`kc.elering.ee`, realm `elering-sso`). There is no simple API key login for consumers — you must obtain a bearer token from your browser session.

## Prerequisites

- Python 3.8+
- `requests` library (`pip install requests`)
- A credentials file at `~/.elering/Elering API Key` (see format below)

## Credentials file format

The script reads `~/.elering/Elering API Key` by default. The file should follow this format (label on one line, value on the next):

```
Elering API Key
Energy Identification Code (EIC)
38ZEE-XXXXXXXXX-X
Client ID
your-client-id-here
Client Secret
your-client-secret-here
```

Authentication uses the **OAuth2 client credentials grant** — no browser login required.

## Run the script

```bash
pip install requests

python fetch_meter_data.py --start 2025-01-01 --end 2025-01-31
```

Save output to a file:

```bash
python fetch_meter_data.py --start 2025-01-01 --end 2025-01-31 --output data.json
```

Download as an export file (CSV/Excel):

```bash
python fetch_meter_data.py --start 2025-01-01 --end 2025-01-31 --export data.xlsx
```

Override the EIC code or use a different credentials file:

```bash
python fetch_meter_data.py --start 2025-01-01 --end 2025-01-31 \
  --eic "38ZEE-XXXXXXXXX-X" \
  --credentials /path/to/other/keyfile
```

## API Details

### Authentication (Keycloak / OpenID Connect)

- **Issuer:** `https://kc.elering.ee/realms/elering-sso`
- **Token endpoint:** `https://kc.elering.ee/realms/elering-sso/protocol/openid-connect/token`
- **OIDC discovery:** `https://kc.elering.ee/realms/elering-sso/.well-known/openid-configuration`
- **Client used by portal:** `efkp`

### Meter data search

```
POST https://datahub.elering.ee/api/v1/meter-data/search
Authorization: Bearer <token>
Content-Type: application/json
```

Request body:
```json
{
  "searchCriteria": {
    "meterEic": "38Z-EE-XXXXXXXXXXXXXXX",
    "periodStart": "2025-01-01T00:00:00Z",
    "periodEnd": "2025-01-31T23:59:59Z"
  },
  "pagination": {
    "page": 0,
    "pageSize": 200
  }
}
```

### Meter data export (file download)

```
POST https://datahub.elering.ee/api/v1/meter-data/export
Authorization: Bearer <token>
Content-Type: application/json
```

### Data resolution

As of April 2025, metering data is recorded in **15-minute intervals** (`PT15M`). Older data may be hourly (`PT1H`).

## Automated / Scheduled Access

The script uses the **client credentials grant** and fetches a fresh token on every run, so it is safe to schedule with cron or any task scheduler:

```cron
# Fetch previous day's data every morning at 06:00
0 6 * * * cd /path/to/estfeed-consumer-api && python fetch_meter_data.py \
  --start $(date -d yesterday +\%Y-\%m-\%d) \
  --end $(date +\%Y-\%m-\%d) \
  --output /path/to/data/$(date -d yesterday +\%Y-\%m-\%d).json
```

## References

- [Estfeed customer portal](https://estfeed.elering.ee)
- [Estfeed Datahub FAQ](https://elering.ee/en/estfeed-datahub-faq)
- [Elering Datahub API docs (GitHub)](https://github.com/Elering/estfeed-datahub-docs)
- [Metering data documentation](https://github.com/Elering/estfeed-datahub-docs/blob/main/eng/12-metering-data.md)
- [Authentication documentation](https://github.com/Elering/estfeed-datahub-docs/blob/main/eng/03-authentication-and-authorisation.md)

# Eufy Cloud API Reference

This documents the Eufy cloud API endpoints discovered during reverse engineering.
These are the same endpoints used by the official Eufy app.

---

## Authentication

### Login

```
POST https://home-api.eufylife.com/v1/user/v2/email/login
Content-Type: application/json

{
  "email": "YOUR_EMAIL",
  "password": "YOUR_PASSWORD",
  "client_type": 1,
  "client_id": "eufylife.com",
  "openudid": "abc123"
}
```

> **Note:** There is also an `api.eufylife.com` login endpoint which returns tokens
> with a `US_` prefix (`VVNf...` in base64). The `home-api.eufylife.com` login returns
> tokens with a different prefix (`ICBf...`). Both work for subsequent API calls.

The response contains an `access_token` field. Use this as the `Authorization` header
for all subsequent requests.

---

## Voice Pack List

Retrieves available voice packs for a given device:

```
GET https://api.eufylife.com/v1/resource/voicePackage?device_id=YOUR_DEVICE_ID
Authorization: YOUR_API_TOKEN
```

### Response schema

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "list": [
      {
        "id": 502,
        "url": "https://d3pkbgk01oouhl.cloudfront.net/upload_file/prod/502_15.zip",
        "version": 15,
        "md5": "abcdef1234567890abcdef1234567890",
        "size": 750000
      },
      ...
    ]
  }
}
```

| Field     | Type   | Description |
|-----------|--------|-------------|
| `id`      | int    | Voice pack ID (use this in DPS 162 `set_id`) |
| `url`     | string | CloudFront download URL |
| `version` | int    | Current version number (increment this when pushing a custom pack) |
| `md5`     | string | Hex MD5 of the ZIP file |
| `size`    | int    | ZIP file size in bytes |

### Known voice pack IDs (T2265, as of early 2025)

The API returns up to 11 voice packs. Confirmed IDs:

| ID  | Folder       | Language/Region     | Version |
|-----|--------------|---------------------|---------|
| 501 | en_us_female | English (US) Female | 13      |
| 502 | en_us_male   | English (US) Male   | 15      |
| *(others)* | | Other languages (DE, FR, ZH, etc.) | varies |

Retrieve the full list with the curl command above using your own token.

---

## CloudFront URL Pattern

Official voice packs are hosted at:
```
https://d3pkbgk01oouhl.cloudfront.net/upload_file/prod/<id>_<version>.zip
```

Example: `https://d3pkbgk01oouhl.cloudfront.net/upload_file/prod/502_15.zip`

---

## Device Information

The device ID and other device details can be retrieved from:

```
GET https://api.eufylife.com/v1/device/home
Authorization: YOUR_API_TOKEN
```

Or from the Eufy app under **Device Settings → Device Info**.

### Additional endpoints discovered

```
GET https://api.eufylife.com/v1/device/setting?device_id=YOUR_DEVICE_ID
```
Returns device settings including `ap_cloud_url`, `iot_url`, `mqtt_url`.

The device uses MQTT for real-time updates via:
```
mqtts://<iot_url>:8883
```

---

## Rate Limiting

The Eufy API aggressively rate-limits repeated requests, especially login attempts.
If you receive `429` or empty responses, wait several minutes before retrying.
Capture your token once and store it — tokens appear to be long-lived.

---

## Notes on Token Prefixes

The `home-api.eufylife.com` token (base64 prefix `ICBf...`) decodes to a string
starting with `  _` (two spaces + underscore). The `api.eufylife.com` token
(base64 prefix `VVNf...`) decodes to `US_`. Despite the difference, both tokens
work interchangeably for the voicePackage API and other `api.eufylife.com` endpoints.

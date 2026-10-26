# Temporary friend access

This optional mode lets friends use the stack running on the host computer without
installing Spark, HDFS, Docker or a local model themselves. They open a temporary
HTTPS URL and enter a username/password in the browser prompt.

```text
Friend browser --HTTPS--> Cloudflare Quick Tunnel
    --> Caddy password gateway --> existing web --> agent / OPA / Spark / HDFS
```

The local web port remains bound to localhost. Neither the gateway nor the tunnel
publishes another host port. All gateway paths, including assets and API status,
require authentication. Caddy validates the original HTTPS Origin for POST before
forwarding a trusted local Origin to the existing backend. Authorization and Cookie
headers are removed upstream. The core analytics code is unchanged.

## Start

Keep Docker, the cluster, Ollama and the local web app running first. Verify
http://localhost:8090 works. Python 3 and Docker CLI are required on the host.

```powershell
python scripts/friend_access.py start
```

On this development machine, if the Python alias does not work:

```powershell
C:/Users/Admin/anaconda3/python.exe scripts/friend_access.py start
```

The script generates a random password, hashes it with bcrypt, validates the gateway
configuration, opens the tunnel and checks the actual external HTTPS route. It
stops the tunnel if verification fails. No account or domain is required for a
Quick Tunnel. The URL may change after restarting it.

Read `.private/friend-access.txt` for the link, username and password. Give these
details only to the intended friends. `.private/` is ignored by Git; credentials
must not be copied into README, reports, screenshots, presentations or GitHub.
Only a password hash is mounted into the gateway. Images are pinned by digest.

## Stop or change password

```powershell
python scripts/friend_access.py stop
python scripts/friend_access.py start --rotate
```

Stop disables external access while leaving the local app running. Rotation stops
the previous tunnel and replaces the shared password. The temporary services have
no automatic restart policy. Browser Basic Auth credentials can be cached; use a
private browser window to test a different account/password.

## Verify

```powershell
python scripts/friend_access.py verify
```

The real HTTPS check covers unauthenticated/wrong-password rejection, authenticated
page and status, private-file 404, cross-origin and missing-Origin rejection, a
missing-period clarification, and the actual 2,040 October 2011 invoice answer with
OPA pre/post decisions. The sanitized report is
`reports/friend-access-verification.json`; it excludes credentials and the URL.

## Limits

This is an authenticated temporary demo, not a deployed multi-user production
service. Anyone with the shared credentials can use it; there are no individual
accounts, per-user isolation or audit identities. Questions are handled one at a
time, and other simultaneous queries receive busy status. The host must remain
awake, connected and running the model/stack. Traffic travels through Cloudflare.
Quick Tunnels are intended for testing/development, not guaranteed availability.

References: [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/),
[Caddy Basic Auth](https://caddyserver.com/docs/caddyfile/directives/basic_auth).

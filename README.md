# Muse Custom Connector: Microsoft 365 Mail (Microsoft Graph)

Give your Muse access to a Microsoft 365 mailbox in your Entra ID tenant: read, search, triage, and, behind strict approval guardrails, send. This is a custom connector for [Muse](https://muse.ai) built on the Microsoft Graph API.

**Why this exists:** Muse's built-in mail connection only supports sign-in with an MSA, a personal Microsoft account. If your mailbox lives in a Microsoft 365 tenant under an Entra ID account, sign-in is declined. This connector is the workaround: your own app registration in your own tenant, delegated permissions, and Muse's secure credential store holding the OAuth credential.

It runs inside Muse. The helper script relies on Muse's credential handling to swap in a live access token, so it is a connector package for Muse users, not a standalone email library.

## What it does

- Reads and triages the connected user's inbox (`triage`)
- Reads a full message as plain text (`read`)
- Searches the mailbox (`search`)
- Reads and sends as a shared mailbox the user has access to (`--mailbox`)
- Sends mail (`send`), locked behind an explicit approval rule (see Guardrails)

## What you need

- A Muse with custom connector support
- A Microsoft 365 tenant where you can register an app, and admin consent for the permissions below (if you are the tenant admin, that is you)
- About 20 minutes

## Setup

Ask your Muse to follow these steps with you. Items marked "you" need your hands, because a secret value is shown exactly once and must go from your screen into Muse's secure setup page without passing through chat.

### 1. Register the app (Azure portal)

In Microsoft Entra ID, create an app registration:

- Name: something recognizable, for example "Muse Mission Control Mail"
- Supported account types: **Accounts in this organizational directory only** (single tenant)
- Redirect URI: leave blank for now

### 2. Add the API permissions and grant consent

Add these Microsoft Graph **delegated** permissions, then grant admin consent for the tenant:

| Permission | What it allows |
|---|---|
| User.Read | Sign in and read the connected user's profile |
| offline_access | Keep the connection alive with a refresh token |
| Mail.Read | Read the user's mail |
| Mail.Read.Shared | Read shared mailboxes the user can access |
| Mail.Send | Send mail as the user |
| Mail.Send.Shared | Send as shared mailboxes the user has Send As rights to |

No application permissions. The connector only ever acts as the signed-in user.

### 3. Enable public client flows (optional, for local script sign-in)

Under Authentication, set **Allow public client flows** to Yes.

### 4. Add the Web redirect URI

Still under Authentication, add a platform, choose **Web**, and add this redirect URI exactly:

```
https://agent.meta.ai/api/hatch/oauth/callback
```

### 5. Create a client secret (you)

Under Certificates & secrets, create a client secret (12 months is a sensible expiry) and copy its **Value** immediately. Microsoft shows it only once. Note the expiry date somewhere you will see it: when the secret lapses, the connection stops until you create a new one and reconnect.

Practical tip for phone setups: the setup page needs two values, the application (client) ID and the secret value, and most phones copy one value at a time. Paste the secret first while it is on screen, then go back for the client ID.

### 6. Connect it in Muse

Register the connection with Muse's custom connector setup (`credentials.request_api_access`), once per tenant:

- Provider slug: pick one per tenant, for example `msgraph-acme`, giving the connection name `custom.msgraph-acme`
- API hosts: `graph.microsoft.com`
- Auth scheme: OAuth 2.0 authorization code
- Issuer domain: `login.microsoftonline.com`
- Authorization URL: `https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/authorize`
- Token URL: `https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token`
- Token endpoint auth method: `client_secret_post`
- Scopes: `offline_access User.Read Mail.Read Mail.Read.Shared Mail.Send Mail.Send.Shared`

On the secure setup page, enter the application (client) ID and the secret value from step 5, then sign in as yourself and approve.

### 7. Install the connector files

Copy this repo's `CONNECTOR.md`, `connector.yaml`, and `bin/` into `~/workspace/custom-connectors/custom.<your-slug>/`, renaming the folder to match your slug. In `CONNECTOR.md`, fill in your provider slug, tenant ID, app IDs, and the secret expiry date. Copy `bin/connector.example.json` to `bin/connector.json` and set `credential` to your connection name, for example `custom.msgraph-acme`.

### 8. Verify

```text
python3 bin/graph_mail.py whoami
python3 bin/graph_mail.py triage --top 10
```

`whoami` should return your account, and `triage` your real inbox, newest first. If either returns 401 or 403, see Troubleshooting.

## Guardrails for sending

Sending is the dangerous half of an email connector, so this package ships with rules, and the script enforces the first one:

- The `send` command refuses to run without an `--approved` flag.
- The calling Muse must show the user the recipients, subject, and full body, and get explicit approval of that exact message, before every send.
- Drafts and sends are separate actions. A draft is never an implicit send.
- Every send is reported to the user with exactly what was shared, and logged.
- No bulk sends, no auto replies, no scheduled sends.
- The kill switch is always available: remove the permissions or disable the app in Entra and access stops immediately.

## Troubleshooting

- **401**: the credential was not attached or was rejected. Confirm the connection is registered and `connector.json` names it correctly. Reconnect only after a request that carried the credential is still rejected.
- **403**: the scopes do not cover the call, consent was not granted, or the user lacks access to that shared mailbox. Check API permissions in the portal first.
- **Redirect mismatch error during setup**: the Web redirect URI in the portal differs from `https://agent.meta.ai/api/hatch/oauth/callback`. Fix it to match exactly.
- **It worked, then stopped months later**: the client secret expired. Create a new one and reconnect.

## Limits

- Delegated access only. The connector reaches what the connected user can reach, nothing tenant-wide.
- One connector per tenant. Two tenants means two registrations, two connections, two connector folders with different slugs.
- The helper covers inbox triage, single-message reads, search, and sending. It does not move, delete, or label messages, and does not read attachments yet.

## License

MIT. See [LICENSE](LICENSE).

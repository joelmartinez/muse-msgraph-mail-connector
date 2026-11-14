# Microsoft Graph Mail, one Entra tenant

- `custom.<your-slug>` connects Muse to one Microsoft 365 tenant through the Microsoft Graph REST API. It authenticates with the registered `oauth2_code` credential and calls only `graph.microsoft.com`. Set up one connector per tenant and give each its own slug, for example `custom.msgraph-acme`.

- The helper is `bin/graph_mail.py` in this folder. It reads and sends mail as the connected user, and can read or send as a shared mailbox the user has access to with `--mailbox`.

- The backing app registration lives in that tenant. Record its name, application (client) ID and directory (tenant) ID here after you create it. IDs are identifiers, not secrets, and are safe to write down. Never write a client secret or token here.

## Connect

- The connection is registered with `credentials.request_api_access`. Fill in the tenant ID and reuse these details to reconnect:

```json
{
  "provider": "<your-slug>",
  "auth_scheme": "oauth2_code",
  "issuer_domain": "login.microsoftonline.com",
  "authorization_url": "https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/authorize",
  "token_url": "https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token",
  "token_endpoint_auth_method": "client_secret_post",
  "scopes": "offline_access User.Read Mail.Read Mail.Read.Shared Mail.Send Mail.Send.Shared",
  "api_hosts": ["graph.microsoft.com"]
}
```

- The app registration carries the Web redirect URI `https://agent.meta.ai/api/hatch/oauth/callback` and one client secret. Record the secret expiry date here so it can be rotated before it lapses: <secret-expiry-date>.

- All six permissions are delegated and must show as granted for the tenant after admin consent. There are no application permissions.

- Copy `bin/connector.example.json` to `bin/connector.json` and set `credential` to the registered connection name, for example `custom.msgraph-acme`.

- Before the first change in a conversation, prove access with a harmless read:

```text
python3 bin/graph_mail.py whoami
```

## Credentials

- The registered connection holds the credential. Helpers import `/opt/muse/skills/custom-connector-setup/bin/dynamic_credentials.py`, which returns an `hsurr:` surrogate and places it where the provider reads the key. Muse swaps in the real credential only on an approved request to a registered host.

- Never put a key, token, password or cookie in this doc, a helper, a command argument, an environment variable or a log. Never ask the user to paste one in chat.

- Keep redirects disabled on authenticated requests.

- On a 401 or 403, check the request first. Confirm that the helper attached the credential, that the host is registered and that the placement and scopes match.

- Only when a request that carried the credential is still rejected, call `credentials.request_api_access` with the details above and `"reconnect": true`.

## Send guardrails

- Never send without the user's explicit approval of the exact message. Show the recipients, the subject and the full body in chat first, every time.

- Drafting and sending are separate actions. Preparing a draft never authorizes a send.

- After any send, report exactly what was shared and log the send.

- No bulk sends, no auto replies and no scheduled sends. Each send is approved on its own.

- The `send` command refuses to run without `--approved`. Pass that flag only after the user approved the exact message in chat.

## Show the connected account

- Run `whoami` to confirm which account the connection acts as.

```text
python3 bin/graph_mail.py whoami
```

## Triage the inbox

- Run `triage` to list recent inbox messages, newest first. Output carries the message id, subject, sender, received time, read state, importance, attachment flag and a body preview. Add `--top N` to change the count and `--mailbox UPN` to read a shared mailbox instead.

```text
python3 bin/graph_mail.py triage --top 15
```

- Results paginate through the `@odata.nextLink` in the response. The helper does not follow it yet, so ask for a larger `--top` when more messages are needed.

## Read one message

- Run `read` with a message id from `triage` or `search`. The body comes back as plain text. Add `--mailbox UPN` for a shared mailbox.

```text
python3 bin/graph_mail.py read --id <message-id>
```

## Search mail

- Run `search` with a query string to search the connected mailbox. Output matches the `triage` fields.

```text
python3 bin/graph_mail.py search --query "invoice" --top 15
```

## Send mail

- Run `send` only under the guardrails above. The message is plain text, is saved to Sent Items, and a 202 response means Microsoft accepted it. Add `--mailbox UPN` to send as a shared mailbox the user has Send As rights to.

```text
python3 bin/graph_mail.py send --to a@example.com --subject "Subject" --body "Body text" --approved
```

## Recover from errors

- A 401 means the credential was missing or rejected. Confirm the helper attached the surrogate and the connection is still registered, then reconnect only if a request that carried the credential is still rejected.

- A 403 means the granted scopes do not cover the call or the user lacks access to that mailbox. Check the permission list in the portal before changing the connector.

- Error responses print the Graph error body as JSON with the HTTP status. Read it before retrying.

- After a failed or timed-out send, check Sent Items with a read before trying again, because the first request may have completed.

## Limits

- Delegated access only. The connector reaches what the connected user can reach, and nothing tenant wide.

- The helper covers the inbox, single message reads, search and sending. It does not move, delete or label messages, and it does not read attachments yet.

- Client secrets expire. When the recorded expiry passes, create a new secret in the portal and reconnect through the secure setup page.

## Related skills

- Use `muse.skill_search` to find other skills and `muse.connector_search` to find other connectors.

#!/usr/bin/env python3
"""Microsoft Graph mail helper for use inside Muse.

Reads and sends mail as the connected user through Microsoft Graph, using the
credential held by a Muse custom connector. The credential never appears
here: dynamic_credentials supplies a surrogate that Muse swaps for the real
access token on requests to graph.microsoft.com.

Which connector to use is read, in order, from:
  1. the MSGRAPH_CONNECTOR environment variable
  2. connector.json beside this script, key "credential"
  3. the default "custom.msgraph-mail"

Commands:
  whoami                                Show the connected account.
  triage [--mailbox UPN] [--top N]      List recent inbox messages.
  read --id ID [--mailbox UPN]          Read one message with its body.
  search --query TEXT [--top N]         Search the connected mailbox.
  send --to ADDR --subject TEXT --body TEXT [--mailbox UPN] --approved
                                        Send mail. Refuses without --approved.
                                        Rule for the calling agent: only invoke
                                        after the user approved the exact
                                        message (recipients, subject, body).
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import add_surrogate_to_request, read_json_response

HOSTS = ["graph.microsoft.com"]
BASE = "https://graph.microsoft.com/v1.0"


def credential_name():
    env = os.environ.get("MSGRAPH_CONNECTOR", "").strip()
    if env:
        return env
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "connector.json")
    try:
        with open(config_path, encoding="utf-8") as handle:
            name = json.load(handle).get("credential", "").strip()
            if name:
                return name
    except (OSError, ValueError):
        pass
    return "custom.msgraph-mail"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused, verify the endpoint")


def call(method, path, params=None, body=None, text_body=False):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if text_body:
        headers["Prefer"] = 'outlook.body-content-type="text"'
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    add_surrogate_to_request(request, credential_name(), allowed_hosts=HOSTS)
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
        if response.status == 202:
            return {"status": 202, "result": "accepted"}
        return read_json_response(response)


def mailbox_base(mailbox):
    if mailbox:
        return "/users/" + urllib.parse.quote(mailbox, safe="")
    return "/me"


def cmd_whoami(args):
    return call("GET", "/me")


def cmd_triage(args):
    base = mailbox_base(args.mailbox)
    params = {
        "$top": args.top,
        "$orderby": "receivedDateTime desc",
        "$select": "id,subject,from,receivedDateTime,isRead,importance,hasAttachments,bodyPreview",
    }
    return call("GET", base + "/mailFolders/inbox/messages", params)


def cmd_read(args):
    base = mailbox_base(args.mailbox)
    params = {"$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,isRead,body"}
    return call("GET", base + "/messages/" + urllib.parse.quote(args.id, safe=""), params, text_body=True)


def cmd_search(args):
    params = {
        "$top": args.top,
        "$search": '"' + args.query + '"',
        "$select": "id,subject,from,receivedDateTime,isRead,bodyPreview",
    }
    return call("GET", "/me/messages", params)


def cmd_send(args):
    if not args.approved:
        raise SystemExit(
            "refused: send requires --approved, and approval means the user "
            "approved this exact message (recipients, subject, body) first"
        )
    base = mailbox_base(args.mailbox)
    recipients = [{"emailAddress": {"address": addr.strip()}} for addr in args.to.split(",") if addr.strip()]
    payload = {
        "message": {
            "subject": args.subject,
            "body": {"contentType": "Text", "content": args.body},
            "toRecipients": recipients,
        },
        "saveToSentItems": True,
    }
    result = call("POST", base + "/sendMail", body=payload)
    return {"sent": True, "to": [r["emailAddress"]["address"] for r in recipients], "subject": args.subject, "result": result}


def main():
    parser = argparse.ArgumentParser(description="Microsoft Graph mail through a Muse custom connector")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("whoami")

    p = sub.add_parser("triage")
    p.add_argument("--mailbox", help="shared mailbox UPN; default is the connected user")
    p.add_argument("--top", type=int, default=15)

    p = sub.add_parser("read")
    p.add_argument("--id", required=True)
    p.add_argument("--mailbox")

    p = sub.add_parser("search")
    p.add_argument("--query", required=True)
    p.add_argument("--top", type=int, default=15)

    p = sub.add_parser("send")
    p.add_argument("--to", required=True, help="comma separated addresses")
    p.add_argument("--subject", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--mailbox", help="send as this shared mailbox; default is the connected user")
    p.add_argument("--approved", action="store_true", help="set only after the user approved this exact message")

    args = parser.parse_args()
    handlers = {
        "whoami": cmd_whoami,
        "triage": cmd_triage,
        "read": cmd_read,
        "search": cmd_search,
        "send": cmd_send,
    }
    try:
        result = handlers[args.command](args)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(json.dumps({"error": exc.code, "detail": detail}, indent=2))
        raise SystemExit(1)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

# Add OraOne to your website

Each assistant can be connected to a website as a chat widget. You choose one of
three ways to install it. All three use the same public widget API.

## Before you start

1. Create an assistant in **Studio**.
2. Open the assistant and choose **Add to website**.
3. Choose **Create chat widget**.
4. Under **Allowed websites**, enter each domain on its own line, for example
   `example.com`. A visitor's site must match one of these domains. Leave the list
   empty to allow any site.
5. Copy the code and paste it on your site. Then choose **Publish widget**.

The widget stays hidden until it is published. Pausing it hides it again.

## Option 1: script tag (any website)

Paste this line before the closing `</body>` tag:

```html
<script src="https://YOUR-DOMAIN/widget.js" data-widget-id="YOUR_PUBLIC_KEY" async></script>
```

Optional attributes:

| Attribute          | Purpose                                                                |
| ------------------ | ---------------------------------------------------------------------- |
| `data-widget-id`   | Required. The widget's public key. It is not a secret.                 |
| `data-api`         | The OraOne API origin, when it is not the same as the script's origin. |
| `data-open="true"` | Opens the chat panel as soon as the page loads.                        |

## Option 2: browser SDK

The script exposes `window.OraOne` once it has loaded. Use the SDK to open the
chat from your own button, to send a message from your code, or to pass
non-secret details about the visitor.

```html
<script src="https://YOUR-DOMAIN/widget.js" data-widget-id="YOUR_PUBLIC_KEY" async></script>
<script>
  window.addEventListener("load", function () {
    window.OraOne.identify({ plan: "pro" }); // optional, never put secrets here
    document.querySelector("#help-button").addEventListener("click", function () {
      window.OraOne.open();
    });
  });
</script>
```

| Method              | Description                                                                                   |
| ------------------- | --------------------------------------------------------------------------------------------- |
| `open()`            | Shows the chat panel.                                                                         |
| `close()`           | Hides the chat panel.                                                                         |
| `toggle()`          | Opens or closes the panel.                                                                    |
| `send(text)`        | Sends a visitor message and opens the panel.                                                  |
| `identify(context)` | Adds context for later messages in this visit. Do not send passwords, tokens or payment data. |
| `destroy()`         | Removes the widget from the page.                                                             |
| `version`           | The loader version, for example `1.0.0`.                                                      |

## Option 3: React or Next.js

Add a component once. It loads the script on the client and removes it on unmount.

```tsx
import { useEffect } from "react";

export function OraOneChat() {
  useEffect(() => {
    const script = document.createElement("script");
    script.src = "https://YOUR-DOMAIN/widget.js";
    script.setAttribute("data-widget-id", "YOUR_PUBLIC_KEY");
    script.async = true;
    document.body.appendChild(script);
    return () => {
      window.OraOne?.destroy();
      script.remove();
    };
  }, []);
  return null;
}
```

## Option 4: REST API (servers and other apps)

Create an API key under **API keys** in Studio (scope `chat:write`). Send it as
`Authorization: Bearer` or `X-API-Key` from your server. Keys are shown once. Store them in your secret manager, never in browser code.

```bash
curl -X POST https://YOUR-DOMAIN/api/v1/chat \
  -H "Authorization: Bearer sk_ora_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are your opening hours?"}'
```

## How the widget keeps visitors safe

- The page only loads the public key and visual settings. Secrets are never sent to the browser.
- Chat requests are checked against the allowed domains and a per-visitor rate limit.
- Visitor text is rendered as plain text. The widget's styles are isolated in a Shadow DOM, so your page's CSS cannot change it.
- Visitors do not sign in. Each visitor gets a random id stored in their browser.

## Troubleshooting

| Symptom                                | Likely cause                                                                          |
| -------------------------------------- | ------------------------------------------------------------------------------------- |
| Nothing appears                        | The widget is not published, or the script tag is not on the page.                    |
| "This chat is not available right now" | The widget is paused, or the site is not in **Allowed websites**.                     |
| Answers are slow or generic            | Add knowledge sources to the assistant, then check the AI key on the server.          |
| Blocked by the browser                 | Check the page's Content Security Policy allows the script origin and the API origin. |

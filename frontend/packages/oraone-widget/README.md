# @oraone/widget

Drop a **Universal AI Agent** — chat with shared memory — into any
modern web app. One agent, every channel, one visitor identity.

## Install

```bash
npm install @oraone/widget
```

## Quick start

```js
import { OraOne } from '@oraone/widget';

OraOne.init({ agentId: 'wgt_your_public_key' });

// The agent recognises this person across every channel:
OraOne.identifyUser({ name: 'Asha', email: 'asha@acme.com' });
```

### React / Next.js

```jsx
import { useEffect } from 'react';
import { OraOne } from '@oraone/widget';

export default function Chat() {
  useEffect(() => {
    OraOne.init({ agentId: 'wgt_your_public_key' });
  }, []);
  return null;
}
```

## SDK methods

| Method | Description |
| --- | --- |
| `OraOne.init(options)` | Boot the widget (agentId, user, context, autoOpen). |
| `OraOne.open()` / `OraOne.close()` | Open / close the chat panel. |
| `OraOne.startChat(message?)` | Open chat and optionally send a first message. |
| `OraOne.identifyUser(traits)` | Attach name/email/phone (recognised everywhere). |
| `OraOne.updateContext(data)` | Merge live page/user context. |
| `OraOne.trackEvent(name, data)` | Send a custom event. |
| `OraOne.setLeadData(data)` | Push qualified lead fields to your CRM. |
| `OraOne.trackPurchase(data)` | Record a purchase / conversion. |

## One-line embed (no build step)

```html
<script src="https://oraone.in/widget.js" data-widget-id="wgt_your_public_key" async></script>
```

Every call made before the loader finishes is buffered and replayed, so call
order never matters. SSR-safe: methods are no-ops on the server.

MIT © OraOne

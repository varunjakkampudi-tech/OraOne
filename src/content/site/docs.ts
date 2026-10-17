import type { SitePage } from "./types";

// Documentation and help. Steps match the product as it works today.

export const docsPages: SitePage[] = [
  {
    kind: "hub",
    path: "/docs",
    title: "Documentation | OraOne",
    eyebrow: "Documentation",
    lead: "Set up an assistant, add it to your website and connect your systems.",
    cards: [
      {
        title: "Quick start",
        text: "From a new account to a live chat on your site.",
        to: "/docs/getting-started",
      },
      {
        title: "Assistants and knowledge",
        text: "Write instructions and upload the documents they answer from.",
        to: "/docs/ai-chat",
      },
      {
        title: "Add to your website",
        text: "Script tag, browser SDK and React component.",
        to: "/docs/integrations",
      },
      { title: "REST API", text: "Send chat from your own servers.", to: "/docs/api" },
      { title: "Webhooks", text: "Receive events at your endpoint.", to: "/docs/webhooks" },
      {
        title: "Help center",
        text: "Answers to common questions and how to get support.",
        to: "/help",
      },
    ],
  },
  {
    kind: "docs",
    path: "/docs/getting-started",
    title: "Quick start | OraOne docs",
    group: "Get started",
    lead: "In about ten minutes you can test an assistant and put it on your site.",
    sections: [
      {
        heading: "1. Sign in",
        body: [
          "Enter your work email. OraOne sends a six-digit code. Type the code to sign in; no password is needed.",
        ],
      },
      {
        heading: "2. Create an assistant",
        body: [
          "Open Assistants, choose New assistant, and give it a name and a purpose. Write a few instructions about how it should talk to customers.",
        ],
      },
      {
        heading: "3. Add knowledge",
        body: [
          "Upload PDF, Word, text or Markdown files that contain the answers your customers need. Uploads are processed before they can be searched.",
        ],
      },
      {
        heading: "4. Test it",
        body: [
          "Open the playground and ask the questions your customers ask. Change the instructions or files until the answers are right.",
        ],
      },
      {
        heading: "5. Add it to your website",
        body: [
          "Open the assistant, choose Add to website, allow your domain and copy the code. Publish the widget when the code is on your site.",
        ],
      },
    ],
    checkpoint:
      "Open your website. The chat bubble should appear. Send a question and check that the answer matches your documents.",
    next: { label: "Add to your website", to: "/docs/integrations" },
  },
  {
    kind: "docs",
    path: "/docs/ai-chat",
    title: "Assistants and knowledge | OraOne docs",
    group: "Build",
    lead: "How assistants use instructions and knowledge to answer.",
    sections: [
      {
        heading: "Instructions",
        body: [
          "Describe the assistant's role, tone and limits. Keep them short and specific: what it helps with, what it must not promise, and when to pass a conversation to a person.",
        ],
      },
      {
        heading: "Knowledge",
        body: [
          "Upload PDF, DOCX, TXT and Markdown files. OraOne reads them, splits them into sections and searches them when a visitor asks a question.",
        ],
      },
      {
        heading: "Sources",
        body: [
          "Each answer lists the documents it used, so you can check it. If the documents do not cover a question, the assistant says so.",
        ],
      },
      {
        heading: "Models",
        body: ["Choose a model for each assistant. The models available depend on your plan."],
      },
    ],
    next: { label: "Add to your website", to: "/docs/integrations" },
  },
  {
    kind: "docs",
    path: "/docs/integrations",
    title: "Add to your website | OraOne docs",
    group: "Build",
    lead: "Three ways to add the chat to a site: a script tag for any site, the browser SDK for control, or a React component.",
    sections: [
      {
        heading: "Option 1: script tag",
        body: [
          "Paste this line before the closing body tag of each page where the chat should appear. Replace the key with the one shown on your install screen.",
        ],
        list: [
          '<script src="https://oraone.in/widget.js" data-widget-id="YOUR_KEY" async></script>',
        ],
      },
      {
        heading: "Option 2: browser SDK",
        body: [
          "After the script loads, window.OraOne is available. Use open(), close(), toggle(), send(text), identify(context) and destroy().",
        ],
        list: ["window.OraOne.open();", "window.OraOne.identify({ plan: 'pro' }); // no secrets"],
      },
      {
        heading: "Option 3: React or Next.js",
        body: [
          "Add a component that loads the script once on the client and removes it when unmounted. The install screen shows the full example.",
        ],
      },
      {
        heading: "Allowed websites",
        body: [
          "List the domains that may show the chat, one per line. Leave the list empty to allow any site.",
        ],
      },
    ],
    checkpoint:
      "Load the page in a private window. The chat bubble should appear, and it should not appear on domains you did not allow.",
    next: { label: "Webhooks", to: "/docs/webhooks" },
  },
  {
    kind: "docs",
    path: "/docs/api",
    title: "REST API | OraOne docs",
    group: "Developers",
    lead: "Send a message to an assistant from your own server and receive the answer as JSON.",
    sections: [
      {
        heading: "Authenticate",
        body: [
          "Create an API key under API keys in the studio. Keys are shown once, so store them in your secret manager. Send the key as an Authorization bearer header or as X-API-Key.",
        ],
      },
      {
        heading: "Send a chat message",
        body: [
          "POST to /api/v1/chat with a JSON body that contains message. Add agent_id to choose an assistant, and conversation_id to continue an earlier conversation.",
        ],
        list: [
          "curl -X POST https://oraone.in/api/v1/chat \\",
          '  -H "Authorization: Bearer YOUR_KEY" \\',
          '  -H "Content-Type: application/json" \\',
          '  -d \'{"message": "What are your opening hours?"}\'',
        ],
      },
      {
        heading: "Read the response",
        body: [
          "The response includes answer, sources (the documents used), conversation_id, model, grounded (whether the answer came from your documents), confidence and usage with token counts and cost.",
        ],
      },
      {
        heading: "Limits",
        body: [
          "Requests are rate-limited per key. A rate-limited request returns HTTP 429 with a message to retry later.",
        ],
      },
    ],
    next: { label: "Webhooks", to: "/docs/webhooks" },
  },
  {
    kind: "docs",
    path: "/docs/webhooks",
    title: "Webhooks | OraOne docs",
    group: "Developers",
    lead: "Receive events at your own endpoint when something happens in OraOne.",
    sections: [
      {
        heading: "Add an endpoint",
        body: [
          "Open Webhooks in the studio, add your HTTPS endpoint and choose the events it should receive.",
        ],
      },
      {
        heading: "Events",
        body: [
          "Available events include conversation.created, conversation.finished, message.created, lead.generated, document.uploaded, document.processed, widget.installed and widget.escalation.",
        ],
      },
      {
        heading: "Delivery and retries",
        body: [
          "Each event is sent as a JSON request. If your endpoint does not respond successfully, OraOne retries a failed delivery up to five times before it stops and records the failure.",
        ],
      },
    ],
  },
  {
    kind: "hub",
    path: "/help",
    title: "Help center | OraOne",
    eyebrow: "Help",
    lead: "Find answers, or contact the team if you are stuck.",
    cards: [
      {
        title: "Quick start",
        text: "Set up an assistant in about ten minutes.",
        to: "/docs/getting-started",
      },
      {
        title: "Add to your website",
        text: "Why the chat is not showing, and how to fix it.",
        to: "/docs/integrations",
      },
      {
        title: "Sign-in codes",
        text: "Codes expire after ten minutes. Request a new one if needed.",
        to: "/auth/sign-in",
      },
      {
        title: "Contact support",
        text: "Send us the details and we will reply.",
        to: "/help/contact",
      },
    ],
  },
  {
    kind: "form",
    path: "/help/contact",
    title: "Contact support | OraOne",
    eyebrow: "Support",
    lead: "Describe the problem and what you expected. Please do not include passwords or API keys.",
    fields: ["name", "email", "message"],
    messageLabel: "What happened?",
    submitLabel: "Review message",
    notice: "Support messages are not sent from this page yet. Your details are checked here only.",
  },
];

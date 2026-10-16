import type { SitePage } from "./types";

// Legal pages are drafts in plain language. They must be reviewed by counsel before
// they are published as final terms. Each page says so at the top.

const UPDATED = "October 2026";

export const legalPages: SitePage[] = [
  {
    kind: "article",
    path: "/privacy",
    title: "Privacy notice | OraOne",
    eyebrow: "Legal",
    lead: "What information OraOne collects, why, and what you can do about it.",
    updated: UPDATED,
    draft: true,
    sections: [
      {
        heading: "Information we collect",
        body: [],
        list: [
          "Account details: your email address and the name you enter.",
          "Business content: assistant instructions, uploaded documents and the conversations your assistants have.",
          "Visitor data from your website: the messages visitors send, the domain they used and details they choose to leave.",
          "Technical data: request logs and security events needed to run and protect the service.",
        ],
      },
      {
        heading: "How we use it",
        body: [
          "We use this information to run OraOne, answer your questions with your assistants, keep accounts secure and improve reliability. We do not sell personal information.",
        ],
      },
      {
        heading: "AI providers",
        body: [
          "To generate answers, the text of a conversation and the relevant parts of your documents are sent to OpenRouter, which passes them to the AI model provider chosen for your assistant.",
        ],
      },
      {
        heading: "Retention and deletion",
        body: [
          "You can delete documents, assistants and conversations from the studio. Deletion from backups follows our retention schedule, which will be published with the final notice.",
        ],
      },
      {
        heading: "Your choices",
        body: [
          "You can ask to see, correct or delete personal information we hold about you by contacting us through the contact page.",
        ],
      },
    ],
  },
  {
    kind: "article",
    path: "/terms",
    title: "Terms of service | OraOne",
    eyebrow: "Legal",
    lead: "The rules for using OraOne.",
    updated: UPDATED,
    draft: true,
    sections: [
      {
        heading: "Using OraOne",
        body: [
          "You must be authorised to act for the business you create. You are responsible for the content you upload and for what your assistants say on your behalf.",
        ],
      },
      {
        heading: "Availability",
        body: [
          "OraOne Product 1 is in development. Features are labelled by status, and features that are not labelled as available may change or not be released.",
        ],
      },
      {
        heading: "Your content",
        body: [
          "You keep ownership of your content. You give us permission to process it to provide the service.",
        ],
      },
      {
        heading: "Acceptable use",
        body: ["Follow the acceptable use rules. We may suspend access that breaks them."],
      },
      {
        heading: "Liability and changes",
        body: [
          "The final liability and warranty terms will be published with the final version. We will announce material changes in advance.",
        ],
      },
    ],
  },
  {
    kind: "article",
    path: "/cookies",
    title: "Cookie notice | OraOne",
    eyebrow: "Legal",
    lead: "The cookies OraOne uses and why.",
    updated: UPDATED,
    draft: true,
    sections: [
      {
        heading: "Essential cookies",
        body: [
          "Session cookies keep you signed in. They are httpOnly, so scripts cannot read them, and they are sent only over HTTPS in production. We cannot run the service without them.",
        ],
      },
      {
        heading: "Preferences",
        body: [
          "A small preference value remembers choices such as the sidebar state. It contains no personal information.",
        ],
      },
      {
        heading: "Analytics",
        body: ["OraOne does not set advertising or third-party tracking cookies on this site."],
      },
    ],
  },
  {
    kind: "article",
    path: "/acceptable-use",
    title: "Acceptable use | OraOne",
    eyebrow: "Legal",
    lead: "What you may and may not do with OraOne.",
    updated: UPDATED,
    draft: true,
    sections: [
      {
        heading: "You may not",
        body: [],
        list: [
          "Use OraOne to send spam, scams or unlawful content",
          "Upload content you do not have the right to use",
          "Try to access another organization's data or bypass rate limits",
          "Use an assistant to pose as a person or impersonate another business",
        ],
      },
      {
        heading: "Enforcement",
        body: [
          "We may remove content, pause assistants or suspend accounts that break these rules.",
        ],
      },
    ],
  },
  {
    kind: "article",
    path: "/refund-policy",
    title: "Refund policy | OraOne",
    eyebrow: "Legal",
    lead: "OraOne does not charge during free access, so there is nothing to refund.",
    updated: UPDATED,
    draft: true,
    sections: [
      {
        heading: "Current position",
        body: ["No payment details are collected and no charges are made during free access."],
      },
      {
        heading: "Before paid plans",
        body: [
          "Before any paid plan starts, we will publish its refund terms and tell account owners in advance.",
        ],
      },
    ],
  },
];

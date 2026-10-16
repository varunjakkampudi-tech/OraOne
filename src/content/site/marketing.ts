import { PRIMARY_CTA, SECONDARY_CTA } from "@/components/site/layout";
import type { SitePage, UseCase } from "./types";

// Marketing pages. Plain language, short copy, and an honest status on every capability.
// Use cases are illustrative examples of the intended workflow, not customers or results.

const USE_CASES: UseCase[] = [
  {
    industry: "Dental clinic",
    problem: "Patients message at night about hours and treatments",
    assistant:
      "answers from the clinic's own FAQ, then collects a name, phone number and preferred time.",
    team: "gets a request to confirm the next morning. The assistant never confirms appointments.",
  },
  {
    industry: "Plumbing and heating",
    problem: "Callers ask about service areas and call-out fees mid-job",
    assistant:
      "explains the areas and fees you have published, then takes the address and a job summary.",
    team: "gets a lead with the job details, ready to dispatch.",
  },
  {
    industry: "Fitness studio",
    problem: "The same questions about classes, trials and memberships",
    assistant: "answers from your timetable and price list, and offers a trial booking request.",
    team: "gets interested prospects in one inbox, and fewer repeat questions at the front desk.",
  },
  {
    industry: "Online shop",
    problem: "Shoppers ask about delivery times, returns and sizing",
    assistant: "answers from your policy pages and passes order-specific problems to a person.",
    team: "gets a short list of questions that need a human, and sees which questions come up most.",
  },
  {
    industry: "Accountancy or law practice",
    problem: "Prospects want to know if you can take on their matter",
    assistant:
      "describes your practice areas and what to prepare. It gives no legal or tax advice.",
    team: "gets a structured intake summary to review.",
  },
  {
    industry: "Letting agency",
    problem: "Tenants ask about deposits, pets and the application steps",
    assistant: "answers from your written policies and takes viewing requests.",
    team: "gets viewing requests in the inbox, and a record of common questions for your listings.",
  },
];

const ASK = SECONDARY_CTA;
const DEMO = PRIMARY_CTA;

export const marketingPages: SitePage[] = [
  {
    kind: "landing",
    path: "/",
    title: "OraOne | AI chat for your website",
    eyebrow: "AI chat for your business",
    hero: {
      title: "Answer website questions, any time of day",
      lead: "OraOne's assistant answers your customers from your own documents, collects their details and passes the rest to your team.",
      primary: DEMO,
      secondary: ASK,
      note: "AI Chat is in active development. Phone and WhatsApp are planned.",
    },
    statusLine: [],
    outcomes: [],
    steps: [
      { title: "Add your information", text: "Upload PDF, Word, text or Markdown files." },
      { title: "Test the answers", text: "Ask the questions your customers ask and adjust." },
      {
        title: "Add the chat to your site",
        text: "Allow your domain and publish when you are ready.",
      },
    ],
    capabilities: [
      {
        title: "Website chat",
        text: "A chat bubble for your site, with suggested questions.",
        status: "available",
      },
      {
        title: "Answers from your documents",
        text: "Replies cite the document they came from.",
        status: "available",
      },
      {
        title: "Team inbox and leads",
        text: "Every conversation and enquiry, with its history.",
        status: "available",
      },
      {
        title: "Staff replies from the inbox",
        text: "Writing back to a visitor from OraOne.",
        status: "in-development",
      },
    ],
    useCases: USE_CASES.slice(0, 6),
    faqs: [
      {
        q: "Do I need a developer?",
        a: "No. Paste one line of code into your site. A developer can use the browser SDK or REST API instead.",
      },
      {
        q: "Where do the answers come from?",
        a: "From the documents you upload. If the documents do not cover a question, the assistant says so.",
      },
      {
        q: "Is the chat live today?",
        a: "AI Chat is in active development. The demo workspace shows how it works, and you can sign in to try it.",
      },
    ],
    showcase: true,
    cta: {
      title: "See how it works",
      text: "Explore the demo workspace, then sign in when you are ready.",
      primary: DEMO,
    },
  },
  {
    kind: "hub",
    path: "/products",
    title: "Products | OraOne",
    eyebrow: "Products",
    lead: "Ten products make up the OraOne family. AI Chat is in active development. The rest are planned or a long-term vision.",
    cards: [],
  },
  {
    kind: "product",
    path: "/products/ai-chat",
    title: "AI Chat | OraOne",
    eyebrow: "Product 1 · In active development",
    hero: {
      title: "AI Chat for your website",
      lead: "An assistant that answers from your documents, shares the conversation with your team and captures leads.",
      primary: DEMO,
      secondary: ASK,
    },
    problem:
      "Customers ask the same questions again and again. Enquiries arrive when nobody is free, and good leads go cold.",
    outcomes: [
      "Visitors get an answer straight away",
      "Each enquiry is saved with its conversation",
      "Your team sees who needs a reply",
    ],
    capabilities: [
      {
        title: "Assistants",
        text: "Write instructions and test answers in the playground.",
        status: "available",
      },
      {
        title: "Knowledge",
        text: "Upload documents. Replies cite their source.",
        status: "available",
      },
      {
        title: "Website widget",
        text: "Script tag, browser SDK or React component.",
        status: "available",
      },
      {
        title: "Team inbox and leads",
        text: "Read history and track each lead's status.",
        status: "available",
      },
      {
        title: "REST API and webhooks",
        text: "Send chat from your systems and receive events.",
        status: "available",
      },
      {
        title: "Staff replies",
        text: "Reply to a visitor from the inbox.",
        status: "in-development",
      },
    ],
    useCases: USE_CASES.slice(0, 3),
    steps: [
      { title: "Create an assistant", text: "Name it and write its first instructions." },
      {
        title: "Add knowledge",
        text: "Upload the files your customers' questions are answered from.",
      },
      { title: "Add it to your site", text: "Allow your domain, copy the code and publish." },
    ],
    faqs: [
      {
        q: "Which AI models are used?",
        a: "Models are hosted through OpenRouter. Your plan decides which models are available.",
      },
      {
        q: "Can I see what the assistant said?",
        a: "Yes. Every conversation is in the inbox, with the sources used for each answer.",
      },
    ],
    showcase: true,
    cta: {
      title: "Try the demo workspace",
      text: "See the inbox, leads and widget with sample data.",
      primary: DEMO,
    },
  },
  {
    kind: "list",
    path: "/features",
    title: "Features | OraOne",
    eyebrow: "Features",
    lead: "Every AI Chat feature with its current status.",
    items: [
      {
        id: "f1",
        title: "Website chat widget",
        text: "Bubble, welcome message and suggested questions.",
        status: "available",
      },
      {
        id: "f2",
        title: "Knowledge uploads",
        text: "PDF, Word, text and Markdown files.",
        status: "available",
      },
      {
        id: "f3",
        title: "Playground",
        text: "Test an assistant before it goes live.",
        status: "available",
      },
      {
        id: "f4",
        title: "Team inbox",
        text: "Conversation history and status.",
        status: "available",
      },
      {
        id: "f5",
        title: "Leads",
        text: "Enquiries from the chat, with status and score.",
        status: "available",
      },
      {
        id: "f6",
        title: "Analytics",
        text: "Conversations by status and top assistants.",
        status: "available",
      },
      {
        id: "f7",
        title: "Team invitations",
        text: "Invite colleagues and manage their access.",
        status: "available",
      },
      {
        id: "f8",
        title: "REST API and webhooks",
        text: "Scoped API keys and event delivery.",
        status: "available",
      },
      {
        id: "f9",
        title: "Staff replies",
        text: "Reply to a visitor from the inbox.",
        status: "in-development",
      },
      {
        id: "f10",
        title: "Phone calls",
        text: "Answer calls with an AI assistant.",
        status: "planned",
      },
      {
        id: "f11",
        title: "WhatsApp",
        text: "Chat on WhatsApp, with voice notes and documents.",
        status: "planned",
      },
      {
        id: "f12",
        title: "Meeting booking",
        text: "Book a meeting from a conversation.",
        status: "planned",
      },
    ],
  },
  {
    kind: "article",
    path: "/platform",
    title: "Platform | OraOne",
    eyebrow: "Platform",
    lead: "One place for every conversation, with an assistant answering first and your team taking over when needed.",
    updated: "October 2026",
    sections: [
      {
        heading: "One inbox",
        body: [
          "Every conversation is recorded with its history, the details collected and the assistant that handled it.",
        ],
      },
      {
        heading: "Assistant first, people when needed",
        body: [
          "The assistant answers from your documents and says when it does not know. Conversations can be handed to your team.",
        ],
      },
      {
        heading: "Connected to your tools",
        body: [
          "The widget, browser SDK, REST API and webhooks connect OraOne to the systems you already use.",
        ],
      },
    ],
  },
  {
    kind: "article",
    path: "/integrations",
    title: "Integrations | OraOne",
    eyebrow: "Integrations",
    lead: "What you can connect today, and what is in development.",
    updated: "October 2026",
    sections: [
      {
        heading: "Available",
        body: [],
        list: [
          "Website: script tag, browser SDK and React component",
          "REST API with scoped keys",
          "Webhooks for conversation, lead and document events",
        ],
      },
      {
        heading: "In development",
        body: [],
        list: ["WhatsApp", "Phone calls", "Email", "Calendar booking"],
      },
    ],
  },
  {
    kind: "hub",
    path: "/solutions",
    title: "Solutions | OraOne",
    eyebrow: "Solutions",
    lead: "How businesses use an assistant day to day.",
    cards: [
      {
        title: "Customer support",
        text: "Answer common questions and pass on the rest.",
        to: "/solutions/customer-support",
      },
      {
        title: "Lead generation",
        text: "Capture enquiries while visitors are still on the page.",
        to: "/solutions/lead-generation",
      },
      {
        title: "Sales",
        text: "Answer product questions from your own material.",
        to: "/solutions/sales",
      },
      {
        title: "Small business",
        text: "A simple front desk that is open outside hours.",
        to: "/solutions/small-business",
      },
    ],
  },
  {
    kind: "product",
    path: "/solutions/customer-support",
    title: "Customer support | OraOne",
    eyebrow: "Solution",
    hero: {
      title: "Answer common questions before they become tickets",
      lead: "Your assistant answers from your help content and gives your team the conversations that need a person.",
      primary: DEMO,
      secondary: ASK,
    },
    problem:
      "Support teams spend much of the day on questions that are already answered in a document.",
    outcomes: [
      "Common questions answered from your help content",
      "Full history for the team",
      "Hard cases passed to a person",
    ],
    capabilities: [
      {
        title: "Answers from help content",
        text: "Upload guides, FAQs and policies.",
        status: "available",
      },
      { title: "Shared inbox", text: "Read every chat and its history.", status: "available" },
      {
        title: "Handover to a person",
        text: "Mark a conversation for your team.",
        status: "available",
      },
    ],
    useCases: USE_CASES.slice(3, 4),
    steps: [
      { title: "Upload help content", text: "Guides, FAQs, returns and opening hours." },
      { title: "Test common questions", text: "Ask what customers ask and check the answers." },
      { title: "Publish", text: "Add the chat where customers look for help." },
    ],
    faqs: [
      {
        q: "What happens to a question the assistant cannot answer?",
        a: "It says so, and the conversation is marked for your team.",
      },
    ],
    cta: {
      title: "Try it with your own help content",
      text: "Explore the demo, then sign in.",
      primary: DEMO,
    },
  },
  {
    kind: "product",
    path: "/solutions/lead-generation",
    title: "Lead generation | OraOne",
    eyebrow: "Solution",
    hero: {
      title: "Turn website visitors into leads",
      lead: "The assistant asks the right questions, records the details and scores each lead for your team.",
      primary: DEMO,
      secondary: ASK,
    },
    problem: "Visitors leave without a trace, or an enquiry waits a day for a reply.",
    outcomes: [
      "Enquiries captured while visitors are on the page",
      "Each lead scored and tracked",
      "A clear list of who needs a reply",
    ],
    capabilities: [
      {
        title: "Lead capture in the chat",
        text: "Name, email and the reason for the enquiry.",
        status: "available",
      },
      {
        title: "Lead status and score",
        text: "Track new, qualified and won leads.",
        status: "available",
      },
      { title: "Lead webhooks", text: "Send new leads to your CRM.", status: "available" },
    ],
    useCases: USE_CASES.slice(1, 2),
    steps: [
      { title: "Choose what to ask", text: "Decide the details the assistant collects." },
      { title: "Publish the widget", text: "Place it where enquiries come from." },
      { title: "Work the list", text: "Follow up qualified leads each day." },
    ],
    faqs: [
      {
        q: "Can leads go to my CRM?",
        a: "Yes, through webhooks that send a lead event to your endpoint.",
      },
    ],
    cta: { title: "Start capturing leads", text: "Explore the demo, then sign in.", primary: DEMO },
  },
  {
    kind: "product",
    path: "/solutions/sales",
    title: "Sales | OraOne",
    eyebrow: "Solution",
    hero: {
      title: "Qualify enquiries before your team calls",
      lead: "The assistant answers product questions from your material and records what each prospect needs.",
      primary: DEMO,
      secondary: ASK,
    },
    problem:
      "Sales teams lose time on enquiries that are not a fit, and can miss the ones that are.",
    outcomes: [
      "Product questions answered from your material",
      "Prospects described by their need",
      "Your team talks to the right people first",
    ],
    capabilities: [
      {
        title: "Product answers",
        text: "Upload brochures, price lists and FAQs.",
        status: "available",
      },
      {
        title: "Qualification notes",
        text: "Each lead records the details from the chat.",
        status: "available",
      },
      { title: "Meeting booking", text: "Book a call from the conversation.", status: "planned" },
    ],
    useCases: USE_CASES.slice(4, 5),
    steps: [
      { title: "Upload sales material", text: "Brochures, price lists and case summaries." },
      { title: "Set qualifying questions", text: "Decide what a good enquiry looks like." },
      { title: "Work qualified leads", text: "Start with leads marked qualified." },
    ],
    faqs: [
      {
        q: "Does the assistant quote prices?",
        a: "Only prices that are in the documents you upload.",
      },
    ],
    cta: {
      title: "Explore with your own material",
      text: "Try the demo, then sign in.",
      primary: DEMO,
    },
  },
  {
    kind: "product",
    path: "/solutions/small-business",
    title: "Small business | OraOne",
    eyebrow: "Solution",
    hero: {
      title: "A front desk that is open outside hours",
      lead: "Set it up in an afternoon with your own information, and keep answering customers while you work.",
      primary: DEMO,
      secondary: ASK,
    },
    problem:
      "A small team cannot be online all day, and every missed message can be a lost customer.",
    outcomes: [
      "Customers answered outside working hours",
      "No technical setup needed",
      "Your information stays in your control",
    ],
    capabilities: [
      { title: "Simple setup", text: "Add documents and publish the widget.", status: "available" },
      { title: "Team access", text: "Invite the people who read the inbox.", status: "available" },
      {
        title: "Usage overview",
        text: "Conversations and leads in analytics.",
        status: "available",
      },
    ],
    useCases: USE_CASES.slice(2, 3),
    steps: [
      {
        title: "Describe your business",
        text: "Hours, services and how you like to be contacted.",
      },
      { title: "Add your information", text: "Price lists, menus or service details." },
      { title: "Publish", text: "Allow your domain and add the chat to your site." },
    ],
    faqs: [
      {
        q: "Do I need technical skills?",
        a: "No. A developer can help, but setup is designed for business owners.",
      },
    ],
    cta: {
      title: "Set up your front desk",
      text: "Explore the demo, then sign in.",
      primary: DEMO,
    },
  },
  {
    kind: "pricing",
    path: "/pricing",
    title: "Pricing | OraOne",
    eyebrow: "Pricing",
    lead: "Free access while AI Chat is in active development. No payment details are collected.",
    plans: [
      {
        name: "Free access",
        price: "Free",
        summary: "Everything in AI Chat while it is in development.",
        items: [
          "Assistants and knowledge uploads",
          "Website widget and browser SDK",
          "Team inbox, leads and analytics",
          "REST API keys and webhooks",
        ],
        cta: DEMO,
      },
    ],
    notes: [
      "No payment details are collected during free access.",
      "Usage limits will be published before any paid plan starts.",
    ],
    faqs: [
      {
        q: "Will I be charged later?",
        a: "Not without notice. Any paid plan will be announced in advance.",
      },
      {
        q: "Can I keep my data if plans change?",
        a: "Yes. Your conversations and documents stay in your account.",
      },
    ],
  },
  {
    kind: "list",
    path: "/roadmap",
    title: "Roadmap | OraOne",
    eyebrow: "Roadmap",
    lead: "What is in development, what is planned and what is a long-term vision. No dates are promised.",
    items: [
      {
        id: "r1",
        title: "AI Chat",
        text: "Website assistants, knowledge, inbox, leads, API and webhooks.",
        status: "active",
      },
      {
        id: "r2",
        title: "Staff replies in the inbox",
        text: "Reply to visitors from OraOne.",
        status: "in-development",
      },
      {
        id: "r3",
        title: "AI Voice Platform",
        text: "Assistants that answer phone calls.",
        status: "planned",
      },
      {
        id: "r4",
        title: "WhatsApp Platform",
        text: "Messaging and automation on WhatsApp.",
        status: "planned",
      },
      {
        id: "r5",
        title: "Omnichannel Communication Hub",
        text: "One inbox for every channel.",
        status: "planned",
      },
      {
        id: "r6",
        title: "Workflow Automation Platform",
        text: "Triggers and actions for follow-ups.",
        status: "planned",
      },
      {
        id: "r7",
        title: "AI Studio & Agent Builder",
        text: "Build and configure your own agents.",
        status: "planned",
      },
      {
        id: "r8",
        title: "Marketplace",
        text: "Agents, templates and connectors.",
        status: "planned",
      },
      {
        id: "r9",
        title: "Mobile Applications",
        text: "Run the business from a phone.",
        status: "planned",
      },
      {
        id: "r10",
        title: "Enterprise Edition",
        text: "Governance and deployment for larger organisations.",
        status: "planned",
      },
      {
        id: "r11",
        title: "OraOne OS",
        text: "A long-term operating layer for AI and business communication.",
        status: "vision",
      },
    ],
  },
  {
    kind: "article",
    path: "/status",
    title: "Status | OraOne",
    eyebrow: "Status",
    lead: "The current state of OraOne.",
    updated: "October 2026",
    sections: [
      {
        heading: "AI Chat",
        body: [
          "AI Chat is in active development. The demo workspace and the widget can be tried. Live services are still being connected, so uptime history is not shown yet.",
        ],
      },
      { heading: "Incidents", body: ["No incidents are recorded here."] },
    ],
  },
  {
    kind: "article",
    path: "/security",
    title: "Security | OraOne",
    eyebrow: "Security",
    lead: "How OraOne protects accounts and business information today.",
    updated: "October 2026",
    sections: [
      {
        heading: "Sign-in",
        body: [
          "Sign-in uses one-time email codes, not passwords. Codes expire after ten minutes and work once.",
          "Sessions use short-lived tokens in httpOnly cookies that scripts cannot read.",
        ],
      },
      {
        heading: "Separation of business data",
        body: [
          "Each organization and workspace is separated on the server. Every request is checked against the member's role.",
        ],
      },
      {
        heading: "Protection against abuse",
        body: [
          "Sign-in and API endpoints are rate-limited. The website chat checks each visitor's domain and request rate.",
        ],
      },
      {
        heading: "Certifications",
        body: [
          "OraOne does not hold formal certifications yet. Certifications and test results will be published here when they exist.",
        ],
      },
    ],
  },
  {
    kind: "article",
    path: "/about",
    title: "About | OraOne",
    eyebrow: "About",
    lead: "OraOne helps businesses answer customers well, at any hour, from their own information.",
    updated: "October 2026",
    sections: [
      {
        heading: "What we are building",
        body: [
          "Assistants that learn a business from its own documents, talk with customers in the channels they use, and hand every enquiry to the team with its details.",
        ],
      },
      {
        heading: "Where we are",
        body: [
          "AI Chat is in active development. Other products are planned or a long-term vision, and each is labelled as such.",
        ],
      },
    ],
  },
  {
    kind: "article",
    path: "/changelog",
    title: "Changelog | OraOne",
    eyebrow: "Changelog",
    lead: "What has changed in OraOne.",
    updated: "October 2026",
    sections: [
      {
        heading: "No public releases yet",
        body: ["Release notes will appear here when a version is published."],
      },
    ],
  },
  {
    kind: "form",
    path: "/contact",
    title: "Contact | OraOne",
    eyebrow: "Contact",
    lead: "Tell us what you need. We reply to business enquiries.",
    fields: ["name", "email", "company", "message"],
    messageLabel: "Your message",
    submitLabel: "Review message",
    notice: "Message delivery is not connected yet, so nothing is sent from this form.",
  },
  {
    kind: "form",
    path: "/demo",
    title: "Book a demo | OraOne",
    eyebrow: "Demo",
    lead: "Tell us what you would like to see. We will show AI Chat with your documents and website.",
    fields: ["name", "email", "company", "message"],
    messageLabel: "What would you like to see?",
    submitLabel: "Review request",
    notice: "Demo booking is not connected yet, so no request is sent from this form.",
  },
];

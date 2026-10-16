import type { SitePage } from "./types";

// Marketing pages: the home page, products, solutions, pricing, company pages and forms.
// Every capability states its real status. Nothing here claims a feature is live
// unless the product supports it today.

const ASK = { label: "Get started", to: "/auth/sign-in" };
const SAMPLE = { label: "See the sample workspace", to: "/app" };

export const marketingPages: SitePage[] = [
  {
    kind: "landing",
    path: "/",
    title: "OraOne | AI chat for your website and customers",
    eyebrow: "AI chat for businesses",
    hero: {
      title: "Answer customers from your own information, any time of day.",
      lead: "OraOne turns the information you already have into an AI assistant for your website. It answers questions, collects enquiries and sends them to your team.",
      primary: ASK,
      secondary: SAMPLE,
      note: "Website chat, the team inbox and leads are available today. Phone and WhatsApp are in development.",
    },
    statusLine: [
      { title: "Website chat", text: "", status: "available" },
      { title: "Team inbox and leads", text: "", status: "available" },
      { title: "Phone and WhatsApp", text: "", status: "in-development" },
    ],
    outcomes: [
      {
        title: "Reply at any hour",
        text: "Your assistant answers the questions you already answer every day, so visitors don't wait for office hours.",
      },
      {
        title: "Capture every enquiry",
        text: "Visitors can leave their details. Each enquiry lands in your inbox with the conversation attached.",
      },
      {
        title: "Stay in control",
        text: "You write the instructions, upload the documents and decide which websites can show the chat.",
      },
    ],
    steps: [
      {
        title: "Teach it your business",
        text: "Upload PDF, Word, text or Markdown files and describe how the assistant should behave.",
      },
      {
        title: "Test it in the playground",
        text: "Ask the questions your customers ask. Adjust the answers until they are right.",
      },
      {
        title: "Add it to your website",
        text: "Paste one line of code, allow your domain and publish. Visitors can chat straight away.",
      },
    ],
    capabilities: [
      {
        title: "Website chat widget",
        text: "A chat bubble for your site, styled in your colours, with suggested questions and a welcome message.",
        status: "available",
      },
      {
        title: "Answers from your knowledge",
        text: "Replies are grounded in the documents you upload. The assistant shows its sources.",
        status: "available",
      },
      {
        title: "Team inbox",
        text: "Every conversation in one place, with its full history and the assistant that answered.",
        status: "available",
      },
      {
        title: "Leads",
        text: "Enquiries from the chat, with status and a lead score for your team to follow up.",
        status: "available",
      },
      {
        title: "Staff replies from the inbox",
        text: "Your team writing back to a visitor from the inbox is not available yet.",
        status: "in-development",
      },
      {
        title: "Phone calls and WhatsApp",
        text: "Answering calls and WhatsApp messages with the same assistant.",
        status: "in-development",
      },
    ],
    faqs: [
      {
        q: "Do I need a developer to add the chat to my website?",
        a: "No. Copy one line of code and paste it before the closing body tag of your site. A developer can also use the browser SDK, React component or REST API.",
      },
      {
        q: "Where do the answers come from?",
        a: "From the documents and information you upload. The assistant says when it cannot find an answer and does not invent one.",
      },
      {
        q: "Can visitors reach a real person?",
        a: "The assistant can hand a conversation to your team. Replying from the inbox is still in development.",
      },
      {
        q: "Is it free?",
        a: "OraOne is free during this access period. No payment details are collected.",
      },
    ],
    cta: {
      title: "Put a helpful assistant on your website today",
      text: "Start with the sample workspace to see how it works, then connect your own information.",
      primary: ASK,
    },
  },
  {
    kind: "hub",
    path: "/products",
    title: "Products | OraOne",
    eyebrow: "Products",
    lead: "AI Chat is available today. Other products in the OraOne plan are in development and are labelled as such.",
    cards: [
      {
        title: "AI Chat",
        text: "Website chat, knowledge answers, the team inbox and leads.",
        to: "/products/ai-chat",
        status: "available",
      },
      {
        title: "Phone and voice",
        text: "Answer calls and missed-call enquiries with an AI assistant.",
        to: "/roadmap",
        status: "in-development",
      },
      {
        title: "WhatsApp",
        text: "Chat with customers and leads on WhatsApp, including voice notes and documents.",
        to: "/roadmap",
        status: "in-development",
      },
      {
        title: "Automation and follow-up",
        text: "Reminders, tasks, meeting booking and follow-up sequences.",
        to: "/roadmap",
        status: "planned",
      },
    ],
  },
  {
    kind: "product",
    path: "/products/ai-chat",
    title: "AI Chat | OraOne",
    eyebrow: "Product 1",
    hero: {
      title: "AI Chat for your website",
      lead: "An assistant that answers from your information, shares it in your team inbox and turns enquiries into leads.",
      primary: ASK,
      secondary: { label: "Read the docs", to: "/docs" },
    },
    problem:
      "Customers ask the same questions again and again, and enquiries arrive when nobody is free to answer. Important leads wait in an unread inbox.",
    outcomes: [
      "Visitors get an answer straight away",
      "Each enquiry is saved with the conversation",
      "Your team sees the leads that need a reply",
    ],
    capabilities: [
      {
        title: "Assistants",
        text: "Write instructions, choose a model and test answers in the playground.",
        status: "available",
      },
      {
        title: "Knowledge",
        text: "Upload PDF, Word, text and Markdown files. Replies cite the source.",
        status: "available",
      },
      {
        title: "Website widget",
        text: "Script tag, browser SDK and React snippet. Allow domains and publish when ready.",
        status: "available",
      },
      {
        title: "Team inbox and leads",
        text: "Read conversations, follow the history and track each lead's status.",
        status: "available",
      },
      {
        title: "Team and access",
        text: "Invite colleagues and choose what each person can change.",
        status: "available",
      },
      {
        title: "REST API and webhooks",
        text: "Send chat from your own systems and receive events at your endpoints.",
        status: "available",
      },
    ],
    steps: [
      {
        title: "Create an assistant",
        text: "Name it, describe its job and write the first instructions.",
      },
      {
        title: "Add knowledge",
        text: "Upload the files that answer your customers' questions.",
      },
      {
        title: "Install on your site",
        text: "Allow your domain, copy the code and publish the widget.",
      },
    ],
    faqs: [
      {
        q: "Which AI models are used?",
        a: "Replies come from OpenRouter-hosted models. The plan you are on decides which models are available.",
      },
      {
        q: "Can I see what the assistant said?",
        a: "Yes. Every conversation is saved in the inbox with the sources used for each answer.",
      },
    ],
    cta: {
      title: "Build your first assistant",
      text: "It takes a few minutes to create one and try it in the playground.",
      primary: ASK,
    },
  },
  {
    kind: "list",
    path: "/features",
    title: "Features | OraOne",
    eyebrow: "Features",
    lead: "Everything in AI Chat, with its current status. Nothing is shown as live unless it works today.",
    items: [
      {
        id: "f1",
        title: "Website chat widget",
        text: "Bubble, welcome message, suggested questions and branding options.",
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
        text: "Conversation history and status for every chat.",
        status: "available",
      },
      {
        id: "f5",
        title: "Leads",
        text: "Enquiries from the chat with status and score.",
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
        text: "Invite colleagues and manage access.",
        status: "available",
      },
      {
        id: "f8",
        title: "REST API and API keys",
        text: "Chat from your own systems with a scoped key.",
        status: "available",
      },
      {
        id: "f9",
        title: "Webhooks",
        text: "Receive conversation, lead and document events.",
        status: "available",
      },
      {
        id: "f10",
        title: "Staff replies",
        text: "Reply to a visitor from the inbox.",
        status: "in-development",
      },
      {
        id: "f11",
        title: "Phone calls",
        text: "Answer calls with an AI assistant.",
        status: "in-development",
      },
      {
        id: "f12",
        title: "WhatsApp",
        text: "Chat on WhatsApp, including voice notes and documents.",
        status: "in-development",
      },
      {
        id: "f13",
        title: "CV and document parsing",
        text: "Pull names, skills and experience from uploaded files.",
        status: "planned",
      },
      {
        id: "f14",
        title: "Meeting booking",
        text: "Book meetings from a conversation.",
        status: "planned",
      },
      {
        id: "f15",
        title: "Follow-up reminders",
        text: "Tasks and sequences over WhatsApp, email or SMS.",
        status: "planned",
      },
    ],
  },
  {
    kind: "article",
    path: "/platform",
    title: "Platform | OraOne",
    eyebrow: "Platform",
    lead: "How OraOne fits into your business: one place for every conversation, with an AI or a person answering.",
    updated: "October 2026",
    sections: [
      {
        heading: "One place for every conversation",
        body: [
          "OraOne records every conversation with its history, the details collected and the assistant that handled it. Your team works from one inbox instead of several tools.",
        ],
      },
      {
        heading: "The assistant answers first",
        body: [
          "Your assistant answers questions from your own documents, collects the details it needs and records the lead. It says so when it does not know an answer.",
        ],
      },
      {
        heading: "People stay in charge",
        body: [
          "Conversations can be handed to a person. Today that means reading the history and following up from your own tools; staff replies inside OraOne are in development.",
        ],
      },
      {
        heading: "Built to connect",
        body: [
          "The website widget, the browser SDK, the REST API and webhooks let OraOne work with the systems you already use.",
        ],
      },
    ],
  },
  {
    kind: "article",
    path: "/integrations",
    title: "Integrations | OraOne",
    eyebrow: "Integrations",
    lead: "Connect OraOne to your website and your systems. These are the integrations available today.",
    updated: "October 2026",
    sections: [
      {
        heading: "Available today",
        body: [],
        list: [
          "Website: a script tag, the browser SDK (window.OraOne) and a React or Next.js component",
          "REST API: chat from your own servers with a scoped API key",
          "Webhooks: conversation, message, lead and document events sent to your endpoint",
        ],
      },
      {
        heading: "In development",
        body: [],
        list: ["WhatsApp", "Phone calls", "Email inbox", "Calendar booking"],
      },
      {
        heading: "Planned",
        body: [],
        list: [
          "npm package for the widget",
          "Social media channels",
          "Google Business and marketplaces",
        ],
      },
    ],
  },
  {
    kind: "landing",
    path: "/solutions",
    title: "Solutions | OraOne",
    eyebrow: "Solutions",
    hero: {
      title: "Find the way OraOne helps your team",
      lead: "Each solution shows how a business uses the AI assistant day to day.",
      primary: ASK,
      secondary: { label: "See pricing", to: "/pricing" },
    },
    statusLine: [],
    outcomes: [],
    steps: [],
    capabilities: [],
    faqs: [],
    cta: {
      title: "Not sure where to start?",
      text: "Book a short demo and we will show you the setup that fits your business.",
      primary: { label: "Book a demo", to: "/demo" },
    },
  },
  {
    kind: "product",
    path: "/solutions/customer-support",
    title: "Customer support | OraOne",
    eyebrow: "Solution",
    hero: {
      title: "Answer support questions before they become tickets",
      lead: "Your assistant handles the common questions from your help content and passes the rest to your team.",
      primary: ASK,
      secondary: SAMPLE,
    },
    problem:
      "Support teams spend their day on questions that are already answered in a document. Customers wait, and the team cannot focus on the hard cases.",
    outcomes: [
      "Common questions answered from your help content",
      "Full conversation history for the team",
      "Hard cases routed to a person",
    ],
    capabilities: [
      {
        title: "Answers from your help content",
        text: "Upload guides, FAQs and policies.",
        status: "available",
      },
      {
        title: "Shared inbox",
        text: "Read every support chat and its history.",
        status: "available",
      },
      {
        title: "Human handover",
        text: "Mark a conversation for a person to take over.",
        status: "available",
      },
      {
        title: "Staff replies in the inbox",
        text: "Reply from OraOne itself.",
        status: "in-development",
      },
    ],
    steps: [
      {
        title: "Upload your help content",
        text: "Guides, FAQs, return policies and opening hours.",
      },
      {
        title: "Test the common questions",
        text: "Ask what your customers ask and check the answers.",
      },
      {
        title: "Publish on your help pages",
        text: "Add the widget where customers look for help.",
      },
    ],
    faqs: [
      {
        q: "What happens to a question the assistant can't answer?",
        a: "It says so and the conversation is marked for your team.",
      },
    ],
    cta: {
      title: "Try it with your own help content",
      text: "Create an assistant and upload one document.",
      primary: ASK,
    },
  },
  {
    kind: "product",
    path: "/solutions/lead-generation",
    title: "Lead generation | OraOne",
    eyebrow: "Solution",
    hero: {
      title: "Turn website visitors into leads you can follow up",
      lead: "The assistant asks the right questions, records the details and gives each lead a score for your team.",
      primary: ASK,
      secondary: SAMPLE,
    },
    problem:
      "Visitors leave without a trace, or send an enquiry that nobody answers for a day. Good leads go cold.",
    outcomes: [
      "Enquiries captured while visitors are still on the page",
      "Each lead scored and marked with its status",
      "A clear list of who needs a reply today",
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
      {
        title: "Lead webhooks",
        text: "Send new leads to your CRM through a webhook.",
        status: "available",
      },
      {
        title: "Automatic follow-up",
        text: "Reminders and sequences for leads.",
        status: "planned",
      },
    ],
    steps: [
      { title: "Decide what to ask", text: "Choose the details the assistant should collect." },
      { title: "Publish the widget", text: "Place it on the pages that bring the most enquiries." },
      { title: "Follow up from the leads list", text: "Work through new leads each day." },
    ],
    faqs: [
      {
        q: "Can leads go to my CRM?",
        a: "Yes, through webhooks, which send a lead event to your endpoint.",
      },
    ],
    cta: {
      title: "Start capturing leads",
      text: "Set up the widget in a few minutes.",
      primary: ASK,
    },
  },
  {
    kind: "product",
    path: "/solutions/sales",
    title: "Sales | OraOne",
    eyebrow: "Solution",
    hero: {
      title: "Qualify enquiries before your sales team spends time on them",
      lead: "Your assistant answers pricing and product questions from your materials and records what each prospect needs.",
      primary: ASK,
      secondary: SAMPLE,
    },
    problem: "Sales teams lose time on enquiries that are not a fit, and miss the ones that are.",
    outcomes: [
      "Product questions answered from your sales material",
      "Prospects described by what they need",
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
        text: "Each lead records the details collected in chat.",
        status: "available",
      },
      {
        title: "Meeting booking",
        text: "Book a call straight from the conversation.",
        status: "planned",
      },
    ],
    steps: [
      { title: "Upload sales material", text: "Brochures, price lists and case summaries." },
      { title: "Set the qualifying questions", text: "Decide what a good enquiry looks like." },
      { title: "Work the qualified leads", text: "Start with the leads marked qualified." },
    ],
    faqs: [
      {
        q: "Does the assistant quote prices?",
        a: "Only if the price is in the documents you upload.",
      },
    ],
    cta: {
      title: "See it with your sales material",
      text: "Book a demo with your own documents.",
      primary: { label: "Book a demo", to: "/demo" },
    },
  },
  {
    kind: "product",
    path: "/solutions/small-business",
    title: "Small business | OraOne",
    eyebrow: "Solution",
    hero: {
      title: "A front desk that never closes, for a small team",
      lead: "Set it up in an afternoon, keep your own information in charge, and answer customers while you run the business.",
      primary: ASK,
      secondary: SAMPLE,
    },
    problem: "A small team cannot be online all day, and each missed message is a lost customer.",
    outcomes: [
      "Customers answered outside working hours",
      "No technical setup needed",
      "Your information stays under your control",
    ],
    capabilities: [
      {
        title: "Simple setup",
        text: "Create an assistant, add documents and publish the widget.",
        status: "available",
      },
      {
        title: "Team access",
        text: "Invite the people who need to see the inbox.",
        status: "available",
      },
      {
        title: "Usage you can see",
        text: "Track conversations and leads in analytics.",
        status: "available",
      },
    ],
    steps: [
      {
        title: "Describe your business",
        text: "Opening hours, services and how you like to be contacted.",
      },
      { title: "Upload your information", text: "Price lists, menus or service details." },
      { title: "Publish", text: "Allow your domain and put the chat on your site." },
    ],
    faqs: [
      {
        q: "Do I need technical skills?",
        a: "No. A developer can help, but the setup is designed for business owners.",
      },
    ],
    cta: {
      title: "Set up your front desk",
      text: "Create your first assistant in minutes.",
      primary: ASK,
    },
  },
  {
    kind: "pricing",
    path: "/pricing",
    title: "Pricing | OraOne",
    eyebrow: "Pricing",
    lead: "OraOne is free during this access period. You can use every AI Chat feature without entering payment details.",
    plans: [
      {
        name: "Free access",
        price: "Free",
        summary: "For testing and early use of AI Chat.",
        items: [
          "Assistants, knowledge uploads and the playground",
          "Website widget and browser SDK",
          "Team inbox, leads and analytics",
          "REST API keys and webhooks",
        ],
        cta: ASK,
      },
    ],
    notes: [
      "No payment details are collected during free access.",
      "Usage limits will be published before any paid plan starts.",
      "Model availability depends on your plan. Some models are reserved for higher plans.",
    ],
    faqs: [
      {
        q: "Will I be charged later?",
        a: "Not without notice. Paid plans, if introduced, will be announced in advance.",
      },
      {
        q: "Can I move my data if plans change?",
        a: "Yes. Your conversations and documents stay in your account.",
      },
    ],
  },
  {
    kind: "article",
    path: "/roadmap",
    title: "Roadmap | OraOne",
    eyebrow: "Roadmap",
    lead: "What is available now, what is in development and what is planned. Dates are not promised.",
    updated: "October 2026",
    sections: [
      {
        heading: "Available",
        body: [],
        list: ["AI Chat: website widget, knowledge, inbox, leads, analytics, API and webhooks"],
      },
      {
        heading: "In development",
        body: [],
        list: ["Staff replies from the inbox", "Phone calls", "WhatsApp", "Email"],
      },
      {
        heading: "Planned",
        body: [],
        list: [
          "npm package",
          "CV and document parsing",
          "Meeting booking",
          "Follow-up sequences",
          "Tasks and reminders",
          "Social media channels",
        ],
      },
    ],
  },
  {
    kind: "article",
    path: "/status",
    title: "Status | OraOne",
    eyebrow: "Status",
    lead: "The current state of OraOne Product 1.",
    updated: "October 2026",
    sections: [
      {
        heading: "Product 1: AI Chat",
        body: [
          "The sample workspace and the widget are available for testing. Live services are being connected, so this page does not show uptime history yet.",
        ],
      },
      {
        heading: "Incidents",
        body: ["No incidents are recorded on this page yet."],
      },
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
          "OraOne uses one-time email codes instead of passwords. Codes expire after ten minutes and can be used once.",
          "Sessions use short-lived access tokens and rotating refresh tokens, stored in secure, httpOnly cookies that scripts cannot read.",
        ],
      },
      {
        heading: "Separation of business data",
        body: [
          "Each organization and workspace is separated on the server. Requests are checked against the signed-in member's role before any data is read or changed.",
        ],
      },
      {
        heading: "Protection against abuse",
        body: [
          "Sign-in and API endpoints are rate-limited. Website chat checks each visitor's domain and request rate.",
        ],
      },
      {
        heading: "What we have not claimed",
        body: [
          "OraOne does not yet hold formal certifications. Certification and penetration test results will be published here when they exist.",
        ],
      },
      {
        heading: "Report a concern",
        body: [
          "Contact the team through the contact page. Please do not include passwords or live credentials.",
        ],
      },
    ],
  },
  {
    kind: "article",
    path: "/about",
    title: "About | OraOne",
    eyebrow: "About",
    lead: "OraOne helps businesses answer customers well, at any hour, with their own information.",
    updated: "October 2026",
    sections: [
      {
        heading: "What we are building",
        body: [
          "AI assistants that understand a business from its own documents, talk with customers on the channels they use, and hand every enquiry to the team with its details.",
        ],
      },
      {
        heading: "Where we are",
        body: [
          "AI Chat is the first product and is available for testing. Other channels and products are in development and are labelled as such on every page.",
        ],
      },
    ],
  },
  {
    kind: "article",
    path: "/changelog",
    title: "Changelog | OraOne",
    eyebrow: "Changelog",
    lead: "Notes on what changed in OraOne.",
    updated: "October 2026",
    sections: [
      {
        heading: "No public releases yet",
        body: [
          "OraOne Product 1 is in development. Release notes will appear here when a version is published.",
        ],
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
    notice:
      "Message delivery is not connected yet, so nothing is sent from this form. Your details are checked on this page only.",
  },
  {
    kind: "form",
    path: "/demo",
    title: "Book a demo | OraOne",
    eyebrow: "Demo",
    lead: "Choose a time to see AI Chat with your own documents and website.",
    fields: ["name", "email", "company", "message"],
    messageLabel: "What would you like to see?",
    submitLabel: "Review request",
    notice:
      "Demo booking is not connected yet, so no request is sent from this form. Your details are checked on this page only.",
  },
];

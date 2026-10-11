export interface OraOneUserTraits {
  name?: string;
  email?: string;
  phone?: string;
  [key: string]: unknown;
}

export interface OraOneInitOptions {
  /** Your widget public key, e.g. "wgt_xxx". */
  agentId?: string;
  /** Override the backend API base (defaults to the embed's data-api). */
  apiBase?: string;
  /** Override the loader script URL. */
  src?: string;
  /** Identify the visitor immediately (recognised across every channel). */
  user?: OraOneUserTraits;
  identify?: OraOneUserTraits;
  /** Arbitrary page/user context merged into the conversation. */
  context?: Record<string, unknown>;
  /** Open the chat panel right after boot. */
  autoOpen?: boolean;
}

export interface OraOneSDK {
  init(options?: OraOneInitOptions): OraOneSDK;
  identifyUser(traits: OraOneUserTraits): OraOneSDK;
  updateContext(data: Record<string, unknown>): OraOneSDK;
  sendEvent(name: string, data?: Record<string, unknown>): OraOneSDK;
  trackEvent(name: string, data?: Record<string, unknown>): OraOneSDK;
  setLeadData(data: Record<string, unknown>): OraOneSDK;
  trackPurchase(data: Record<string, unknown>): OraOneSDK;
  open(): OraOneSDK;
  close(): OraOneSDK;
  toggle(): OraOneSDK;
  openChat(): OraOneSDK;
  closeChat(): OraOneSDK;
  toggleChat(): OraOneSDK;
  startChat(message?: string): OraOneSDK;
}

export const OraOne: OraOneSDK;
export const OraOneWidget: OraOneSDK;
export default OraOne;

import { createContext, useContext } from "react";
import { sampleWorkspaceName } from "@/lib/oraone";

// The workspace shown in the shell. Context values are kept referentially stable by
// the provider in components/oraone/shell.tsx.
export const WorkspaceContext = createContext({ workspace: sampleWorkspaceName, sample: true });

export const useWorkspace = () => useContext(WorkspaceContext);

"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { HttpAgent } from "@ag-ui/client";

const COPILOTKIT_ENDPOINT =
  process.env.NEXT_PUBLIC_COPILOTKIT_ENDPOINT || "http://localhost:8000/api/copilotkit";

export function CopilotKitWrapper({ children }) {
  return (
    <CopilotKit
      agents__unsafe_dev_only={{
        default: new HttpAgent({ url: COPILOTKIT_ENDPOINT }),
      }}
    >
      {children}
    </CopilotKit>
  );
}

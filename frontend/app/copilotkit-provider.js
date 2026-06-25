"use client";

import { CopilotKit } from "@copilotkit/react-core/v2";
import { HttpAgent } from "@copilotkit/react-core/v2";
import { COPILOTKIT_ENDPOINT } from "./lib/config";

const agentInstance = new HttpAgent({ url: COPILOTKIT_ENDPOINT });

export function CopilotKitWrapper({ children }) {
  return (
    <CopilotKit
      agents__unsafe_dev_only={{
        default: agentInstance,
      }}
    >
      {children}
    </CopilotKit>
  );
}

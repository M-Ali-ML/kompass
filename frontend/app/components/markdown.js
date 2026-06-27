import { CopilotChatAssistantMessage } from "@copilotkit/react-core/v2";

// Renders a markdown string using the same renderer CopilotKit uses for
// assistant messages (Streamdown), so grounded research / transit answers show
// proper headings, lists and bold instead of raw "###" and "**" syntax.
// `kompass-markdown` (globals.css) keeps the typography compact and on-brand
// for the tighter tool-card surface.
export function Markdown({ content, className = "" }) {
  return (
    <div className={`kompass-markdown ${className}`}>
      <CopilotChatAssistantMessage.MarkdownRenderer content={content} />
    </div>
  );
}

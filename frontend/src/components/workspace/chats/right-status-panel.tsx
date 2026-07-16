import type { Message } from "@langchain/langgraph-sdk";
import { BotIcon, ListChecksIcon, MonitorIcon, TerminalIcon } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";

import { ConversationEmptyState } from "@/components/ai-elements/conversation";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { findToolCallResult } from "@/core/messages/utils";
import { cn } from "@/lib/utils";

import { useThread } from "../messages/context";

interface BashStep {
  id: string;
  command?: string;
  result?: string;
  running: boolean;
}

interface TodoItem {
  content: string;
  status: "pending" | "in_progress" | "completed";
}

// ponytail: reuses the write_todos tool_calls that already flow through
// thread.messages (message-group.tsx renders them as a bare "Write Todos"
// chain-of-thought step today) — take the most recent call's full list as
// current plan state. No new backend event, no research.stage equivalent
// needed (Aio's ResearchPlanCard source event doesn't exist here).
function extractLatestTodos(messages: Message[]): TodoItem[] {
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i];
    if (message?.type !== "ai") continue;
    const toolCalls = message.tool_calls ?? [];
    for (let j = toolCalls.length - 1; j >= 0; j--) {
      const toolCall = toolCalls[j];
      if (toolCall?.name !== "write_todos") continue;
      const todos = (toolCall.args as { todos?: TodoItem[] } | undefined)
        ?.todos;
      if (todos?.length) return todos;
    }
  }
  return [];
}

// ponytail: reuses the same tool_calls/tool-result data that already drives
// the chain-of-thought steps in message-group.tsx (`convertToSteps`), just
// filtered to `bash` — no new stream plumbing needed, `thread.messages` is
// already live/reactive via useStream.
function extractBashSteps(messages: Message[]): BashStep[] {
  const steps: BashStep[] = [];
  for (const message of messages) {
    if (message.type !== "ai") continue;
    for (const toolCall of message.tool_calls ?? []) {
      if (toolCall.name !== "bash" || !toolCall.id) continue;
      const command = (toolCall.args as { command?: string } | undefined)
        ?.command;
      steps.push({
        id: toolCall.id,
        command,
        result: findToolCallResult(toolCall.id, messages),
        running: !findToolCallResult(toolCall.id, messages),
      });
    }
  }
  return steps;
}

export function RightStatusPanel({ className }: { className?: string }) {
  const { thread } = useThread();
  const isRunning = thread.isLoading;
  const bashSteps = useMemo(
    () => extractBashSteps(thread.messages),
    [thread.messages],
  );
  const todos = useMemo(
    () => extractLatestTodos(thread.messages),
    [thread.messages],
  );
  const terminalScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = terminalScrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [bashSteps]);

  return (
    <div className={cn("flex h-full flex-col gap-4 p-4", className)}>
      <div className="glass-surface flex items-center gap-3 rounded-lg p-4">
        <div className="icon-badge-glass flex h-10 w-10 shrink-0 items-center justify-center rounded-full">
          <BotIcon className="text-primary size-5" />
        </div>
        <div className="flex min-w-0 flex-col gap-0.5">
          <span className="text-sm font-medium">Agent</span>
          <span className="text-muted-foreground flex items-center gap-1.5 text-xs">
            <span
              className={cn(
                "size-1.5 rounded-full",
                isRunning ? "bg-primary animate-pulse" : "bg-muted-foreground/50",
              )}
            />
            {isRunning ? "Running" : "Idle"}
          </span>
        </div>
      </div>

      {/* ponytail: usage stats need a backend endpoint, not built yet */}
      <p className="text-muted-foreground -mt-2 px-1 text-xs">
        Usage tracking coming soon
      </p>

      {/* ponytail: terminal chrome now theme-aware (muted/card tokens) instead of
          hardcoded dark — user flagged pitch-black chrome as wrong in light mode. */}
      <Tabs defaultValue="terminal" className="min-h-0 flex-1 gap-2">
        <TabsList variant="line" className="shrink-0">
          <TabsTrigger value="terminal" className="gap-1.5 font-mono">
            <TerminalIcon className="size-4" />
            Terminal
          </TabsTrigger>
          <TabsTrigger value="preview" className="gap-1.5 font-mono">
            <MonitorIcon className="size-4" />
            Preview
          </TabsTrigger>
        </TabsList>

        <TabsContent
          value="terminal"
          className="border-border bg-card min-h-0 overflow-hidden rounded-lg border"
        >
          <div
            ref={terminalScrollRef}
            className="size-full overflow-y-auto p-3 font-mono text-xs"
          >
            {bashSteps.length === 0 ? (
              <ConversationEmptyState
                className="text-muted-foreground size-full [&_h3]:text-xs [&_p]:text-xs"
                icon={<TerminalIcon className="size-5" />}
                title="No output yet"
                description="Terminal output appears here once the agent runs commands."
              />
            ) : (
              <div className="flex flex-col gap-3">
                {bashSteps.map((step) => (
                  <div key={step.id}>
                    <div className="text-primary">$ {step.command}</div>
                    {step.result && (
                      <pre className="text-muted-foreground mt-1 whitespace-pre-wrap">
                        {step.result}
                      </pre>
                    )}
                    {step.running && (
                      <span className="text-muted-foreground animate-pulse">
                        running…
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent
          value="preview"
          className="border-border bg-card min-h-0 overflow-hidden rounded-lg border"
        >
          {todos.length === 0 ? (
            <ConversationEmptyState
              className="text-muted-foreground size-full p-4 text-xs [&_h3]:text-xs [&_p]:text-xs"
              icon={<MonitorIcon className="size-5" />}
              title="No research output yet"
              description="Research results will appear here once the agent starts a research task."
            />
          ) : (
            <div className="size-full overflow-y-auto p-3 text-xs">
              <div className="mb-2 flex items-center gap-1.5 font-medium">
                <ListChecksIcon className="size-4" />
                Plan
              </div>
              <ol className="flex list-decimal list-outside flex-col gap-1.5 pl-6">
                {todos.map((todo, i) => (
                  <li
                    key={i}
                    className={cn(
                      "marker:text-muted-foreground",
                      todo.status === "completed" &&
                        "text-muted-foreground line-through",
                      todo.status === "in_progress" && "text-primary",
                      todo.status === "pending" && "text-foreground",
                    )}
                  >
                    {todo.content}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

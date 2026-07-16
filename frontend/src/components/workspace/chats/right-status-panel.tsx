import type { Message } from "@langchain/langgraph-sdk";
import {
  BotIcon,
  FilesIcon,
  MonitorIcon,
  TerminalIcon,
  XIcon,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ConversationEmptyState } from "@/components/ai-elements/conversation";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { findToolCallResult } from "@/core/messages/utils";
import { useIsMobile } from "@/hooks/use-mobile";
import { cn } from "@/lib/utils";

import {
  ArtifactFileDetail,
  ArtifactFileList,
  useArtifacts,
} from "../artifacts";
import { useThread } from "../messages/context";

import { SandboxTerminal } from "./sandbox-terminal";

export interface BashStep {
  id: string;
  command?: string;
  result?: string;
  running: boolean;
}

// ponytail: mirrors extractBashSteps below, filtered to the `preview` tool —
// take the latest successful call's result (a URL string) as the live
// dev-server preview. Plan/todos already render in message-group.tsx's
// chain-of-thought, no need to duplicate them here.
function extractLatestPreviewUrl(messages: Message[]): string | undefined {
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i];
    if (message?.type !== "ai") continue;
    const toolCalls = message.tool_calls ?? [];
    for (let j = toolCalls.length - 1; j >= 0; j--) {
      const toolCall = toolCalls[j];
      if (toolCall?.name !== "preview" || !toolCall.id) continue;
      const result = findToolCallResult(toolCall.id, messages);
      if (result && !result.startsWith("Error")) return result;
    }
  }
  return undefined;
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

export function RightStatusPanel({
  className,
  threadId,
  artifactPanelOpen,
}: {
  className?: string;
  threadId: string;
  artifactPanelOpen: boolean;
}) {
  const { thread } = useThread();
  const isRunning = thread.isLoading;
  const isMobile = useIsMobile();
  const {
    artifacts,
    selectedArtifact,
    setOpen: setArtifactsOpen,
  } = useArtifacts();

  const bashSteps = useMemo(
    () => extractBashSteps(thread.messages),
    [thread.messages],
  );
  const previewUrl = useMemo(
    () => extractLatestPreviewUrl(thread.messages),
    [thread.messages],
  );

  const [tab, setTab] = useState(selectedArtifact ? "files" : "terminal");
  useEffect(() => {
    if (selectedArtifact) setTab("files");
  }, [selectedArtifact]);

  const filesTab = selectedArtifact ? (
    <ArtifactFileDetail
      className="size-full"
      filepath={selectedArtifact}
      threadId={threadId}
    />
  ) : (
    <div className="relative flex size-full justify-center">
      <div className="absolute top-1 right-1 z-30">
        <Button
          size="icon-sm"
          variant="ghost"
          onClick={() => {
            setArtifactsOpen(false);
          }}
        >
          <XIcon />
        </Button>
      </div>
      {artifacts.length === 0 ? (
        <ConversationEmptyState
          icon={<FilesIcon />}
          title="No artifact selected"
          description="Select an artifact to view its details"
        />
      ) : (
        <div className="flex size-full max-w-(--container-width-sm) flex-col justify-center p-4 pt-8">
          <header className="shrink-0">
            <h2 className="text-lg font-medium">Artifacts</h2>
          </header>
          <main className="min-h-0 grow">
            <ArtifactFileList
              className="max-w-(--container-width-sm) p-4 pt-12"
              files={artifacts}
              threadId={threadId}
            />
          </main>
        </div>
      )}
    </div>
  );

  // ponytail: mobile keeps the old artifacts-only surface (no Terminal/Preview
  // chrome) — same slide transition it always had, just relocated here.
  if (isMobile) {
    return (
      <div
        className={cn(
          "h-full p-4 transition-transform duration-300 ease-in-out",
          artifactPanelOpen ? "translate-x-0" : "translate-x-full",
        )}
      >
        {filesTab}
      </div>
    );
  }

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
      <Tabs
        value={tab}
        onValueChange={setTab}
        className="min-h-0 flex-1 gap-2"
      >
        <TabsList variant="line" className="shrink-0">
          <TabsTrigger value="files" className="gap-1.5 font-mono">
            <FilesIcon className="size-4" />
            Files
          </TabsTrigger>
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
          value="files"
          className="border-border bg-card min-h-0 overflow-hidden rounded-lg border"
        >
          {filesTab}
        </TabsContent>

        <TabsContent
          value="terminal"
          className="border-border bg-card min-h-0 overflow-hidden rounded-lg border"
        >
          {bashSteps.length === 0 ? (
            <ConversationEmptyState
              className="text-muted-foreground size-full p-3 [&_h3]:text-xs [&_p]:text-xs"
              icon={<TerminalIcon className="size-5" />}
              title="No output yet"
              description="Terminal output appears here once the agent runs commands."
            />
          ) : (
            <SandboxTerminal steps={bashSteps} />
          )}
        </TabsContent>

        <TabsContent
          value="preview"
          className="border-border bg-card min-h-0 overflow-hidden rounded-lg border"
        >
          {previewUrl ? (
            <iframe
              className="size-full"
              src={previewUrl}
              title="Live preview"
            />
          ) : (
            <ConversationEmptyState
              className="text-muted-foreground size-full p-4 text-xs [&_h3]:text-xs [&_p]:text-xs"
              icon={<MonitorIcon className="size-5" />}
              title="No preview yet"
              description="Live preview appears here once the agent starts a dev server in the sandbox."
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

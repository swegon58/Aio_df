import type { Message } from "@langchain/langgraph-sdk";
import { BotIcon, Code2Icon, FilesIcon, MonitorIcon, XIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

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

// ponytail: take the latest successful `preview` tool call's result (a URL
// string) as the live dev-server preview. Plan/todos already render in
// message-group.tsx's chain-of-thought, no need to duplicate them here.
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

  const previewUrl = useMemo(
    () => extractLatestPreviewUrl(thread.messages),
    [thread.messages],
  );

  const [tab, setTab] = useState("code");
  useEffect(() => {
    if (selectedArtifact) setTab("code");
  }, [selectedArtifact]);

  // ponytail: Radix unmounts the inactive TabsContent, so switching back into
  // "code" remounts ArtifactFileDetail and its auto-view-mode effect fires
  // again — without this guard it immediately snaps back to "preview" and
  // the Code tab becomes unreachable. Only auto-open preview once per
  // artifact, not on every remount.
  const autoPreviewedArtifactRef = useRef<string | null>(null);
  const handleAutoViewMode = useCallback(
    (mode: "code" | "preview") => {
      if (mode !== "preview") return;
      if (autoPreviewedArtifactRef.current === selectedArtifact) return;
      autoPreviewedArtifactRef.current = selectedArtifact ?? null;
      setTab("preview");
    },
    [selectedArtifact],
  );

  const codeTab = selectedArtifact ? (
    <ArtifactFileDetail
      className="size-full"
      filepath={selectedArtifact}
      threadId={threadId}
      viewMode="code"
      onAutoViewMode={handleAutoViewMode}
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

  // ponytail: mobile keeps the old artifacts-only surface (no Preview chrome)
  // — same slide transition it always had, just relocated here.
  if (isMobile) {
    return (
      <div
        className={cn(
          "h-full p-4 transition-transform duration-300 ease-in-out",
          artifactPanelOpen ? "translate-x-0" : "translate-x-full",
        )}
      >
        {codeTab}
      </div>
    );
  }

  const previewTab = previewUrl ? (
    <iframe className="size-full" src={previewUrl} title="Live preview" />
  ) : selectedArtifact ? (
    <ArtifactFileDetail
      className="size-full"
      filepath={selectedArtifact}
      threadId={threadId}
      viewMode="preview"
    />
  ) : (
    <ConversationEmptyState
      className="text-muted-foreground size-full p-4 text-xs [&_h3]:text-xs [&_p]:text-xs"
      icon={<MonitorIcon className="size-5" />}
      title="No preview yet"
      description="Live preview appears here once the agent starts a dev server in the sandbox."
    />
  );

  return (
    // ponytail: `relative` isn't cosmetic — the fixed DotGrid canvas behind
    // workspace content paints in the CSS z-index:0 stacking step, which sits
    // ABOVE non-positioned static content. Without this, the dot canvas
    // renders on top of Code/Preview at 60% opacity, looking like a
    // transparent panel with a background showing through.
    <div className={cn("relative flex h-full flex-col gap-4 p-4", className)}>
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

      <Tabs
        value={tab}
        onValueChange={setTab}
        className="min-h-0 flex-1 gap-2"
      >
        <TabsList variant="line" className="shrink-0">
          <TabsTrigger value="code" className="gap-1.5 font-mono">
            <Code2Icon className="size-4" />
            Code
          </TabsTrigger>
          <TabsTrigger value="preview" className="gap-1.5 font-mono">
            <MonitorIcon className="size-4" />
            Preview
          </TabsTrigger>
        </TabsList>

        <TabsContent
          value="code"
          className="border-border bg-card min-h-0 overflow-hidden rounded-lg border"
        >
          {codeTab}
        </TabsContent>

        <TabsContent
          value="preview"
          className="border-border bg-card min-h-0 overflow-hidden rounded-lg border"
        >
          {previewTab}
        </TabsContent>
      </Tabs>
    </div>
  );
}

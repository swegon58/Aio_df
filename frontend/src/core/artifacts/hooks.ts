import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { useThread } from "@/components/workspace/messages/context";

import { loadArtifactContent, loadArtifactContentFromToolCall } from "./loader";

export function useArtifactContent({
  filepath,
  threadId,
  enabled,
  toolResult,
}: {
  filepath: string;
  threadId: string;
  enabled?: boolean;
  toolResult?: string;
}) {
  const isWriteFile = useMemo(() => {
    return filepath.startsWith("write-file:");
  }, [filepath]);
  const { thread, isMock } = useThread();
  const draftContent = useMemo(() => {
    if (isWriteFile) {
      return loadArtifactContentFromToolCall({ url: filepath, thread });
    }
    return null;
  }, [filepath, isWriteFile, thread]);

  // Draft reconstruction only understands write_file tool-call args. Other
  // file-editing tools (e.g. str_replace) leave no reconstructable draft, so
  // once that tool call has finished, fall back to fetching the real file.
  const realPath = useMemo(() => {
    if (!isWriteFile) {
      return undefined;
    }
    try {
      return decodeURIComponent(new URL(filepath).pathname);
    } catch {
      return undefined;
    }
  }, [filepath, isWriteFile]);
  const needsRealFetch =
    isWriteFile &&
    draftContent === undefined &&
    toolResult !== undefined &&
    !!realPath;

  const { data, isLoading, error } = useQuery({
    // Cache key must be the full write-file URL (unique per tool call), not
    // realPath — realPath is shared across every edit to the same file, so
    // keying on it would serve stale cached content from an earlier tool
    // call after a later str_replace/write_file changes the real file.
    queryKey: ["artifact", filepath, threadId, isMock],
    queryFn: () => {
      return loadArtifactContent({
        filepath: (isWriteFile ? realPath : filepath) ?? "",
        threadId,
        isMock,
      });
    },
    enabled: isWriteFile ? enabled && needsRealFetch : enabled,
    // Cache artifact content for 5 minutes to avoid repeated fetches (especially for .skill ZIP extraction)
    staleTime: 5 * 60 * 1000,
  });
  return {
    content: isWriteFile ? (draftContent ?? data?.content) : data?.content,
    url: isWriteFile ? undefined : data?.url,
    isLoading: isWriteFile ? needsRealFetch && isLoading : isLoading,
    error,
  };
}

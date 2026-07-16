import { DownloadIcon, LoaderIcon, PackageIcon } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { urlOfArtifact } from "@/core/artifacts/utils";
import { useI18n } from "@/core/i18n/hooks";
import { installSkill } from "@/core/skills/api";
import {
  getFileExtension,
  getFileExtensionDisplayName,
  getFileIcon,
  getFileName,
} from "@/core/utils/files";
import { cn } from "@/lib/utils";

import { useArtifacts } from "./context";

const IMAGE_EXTENSIONS = new Set([
  "jpg",
  "jpeg",
  "png",
  "gif",
  "bmp",
  "tiff",
  "ico",
  "webp",
  "svg",
  "heic",
]);

export function ArtifactFileList({
  className,
  files,
  threadId,
}: {
  className?: string;
  files: string[];
  threadId: string;
}) {
  const { t } = useI18n();
  const { select: selectArtifact, setOpen } = useArtifacts();
  const [installingFile, setInstallingFile] = useState<string | null>(null);

  const handleClick = useCallback(
    (filepath: string) => {
      selectArtifact(filepath);
      setOpen(true);
    },
    [selectArtifact, setOpen],
  );

  const handleInstallSkill = useCallback(
    async (e: React.MouseEvent, filepath: string) => {
      e.stopPropagation();
      e.preventDefault();

      if (installingFile) return;

      setInstallingFile(filepath);
      try {
        const result = await installSkill({
          thread_id: threadId,
          path: filepath,
        });
        if (result.success) {
          toast.success(result.message);
        } else {
          toast.error(result.message || "Failed to install skill");
        }
      } catch (error) {
        console.error("Failed to install skill:", error);
        toast.error("Failed to install skill");
      } finally {
        setInstallingFile(null);
      }
    },
    [threadId, installingFile],
  );

  const { imageFiles, otherFiles } = useMemo(() => {
    const imageFiles: string[] = [];
    const otherFiles: string[] = [];
    for (const file of files) {
      (IMAGE_EXTENSIONS.has(getFileExtension(file)) ? imageFiles : otherFiles).push(
        file,
      );
    }
    return { imageFiles, otherFiles };
  }, [files]);

  return (
    <div className={cn("flex w-full flex-col gap-4", className)}>
      <div className="panel-section panel-section--files">
        <div className="panel-section-heading">Gallery</div>
        {imageFiles.length > 0 ? (
          <div className="gallery-grid">
            {imageFiles.map((file) => (
              <button
                key={file}
                type="button"
                className="gallery-thumb"
                onClick={() => handleClick(file)}
              >
                <img
                  src={urlOfArtifact({ filepath: file, threadId })}
                  alt={getFileName(file)}
                />
              </button>
            ))}
          </div>
        ) : (
          <p className="text-muted-foreground px-1 py-2 text-xs">
            No images yet
          </p>
        )}
      </div>

      <div className="panel-section">
        <div className="panel-section-heading">Files</div>
        {otherFiles.length > 0 ? (
          <ul className="today-card-grid">
            {otherFiles.map((file) => (
              <li key={file}>
                <div
                  className="today-card"
                  role="button"
                  tabIndex={0}
                  onClick={() => handleClick(file)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") handleClick(file);
                  }}
                >
                  <div className="today-card-topline">
                    {getFileIcon(file, "size-4")}
                    <span className="today-card-source">
                      {getFileExtensionDisplayName(file)} file
                    </span>
                  </div>
                  <div className="today-card-title">{getFileName(file)}</div>
                  <div className="today-card-actions">
                    {file.endsWith(".skill") && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="today-card-icon-action"
                        disabled={installingFile === file}
                        onClick={(e) => handleInstallSkill(e, file)}
                      >
                        {installingFile === file ? (
                          <LoaderIcon className="size-4 animate-spin" />
                        ) : (
                          <PackageIcon className="size-4" />
                        )}
                        {t.common.install}
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" asChild>
                      <a
                        href={urlOfArtifact({
                          filepath: file,
                          threadId: threadId,
                          download: true,
                        })}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <DownloadIcon className="size-4" />
                        {t.common.download}
                      </a>
                    </Button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground px-1 py-2 text-xs">
            No files yet
          </p>
        )}
      </div>
    </div>
  );
}

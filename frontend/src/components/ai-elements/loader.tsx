import { cn } from "@/lib/utils";
import type { CSSProperties, HTMLAttributes } from "react";

export type LoaderProps = HTMLAttributes<HTMLDivElement> & {
  size?: number;
};

// ponytail: bounce-square material lifted from uiverse.io/R5Program/jolly-goat-11
// (see .loader-bounce in globals.css); this is the single shared Loader — reuse
// it for any future loading state instead of adding a new spinner.
export const Loader = ({ className, size = 16, style, ...props }: LoaderProps) => (
  <div
    className={cn("loader-bounce", className)}
    style={{ "--loader-size": `${size}px`, ...style } as CSSProperties}
    {...props}
  >
    <div className="loader-bounce-square" />
    <div className="loader-bounce-square" />
    <div className="loader-bounce-square" />
  </div>
);

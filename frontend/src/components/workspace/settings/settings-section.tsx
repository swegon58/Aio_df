import { cn } from "@/lib/utils";

export function SettingsSection({
  className,
  title,
  description,
  action,
  children,
}: {
  className?: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className={cn(className)}>
      <header className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <div className="font-heading text-lg font-semibold">{title}</div>
          {action}
        </div>
        {description && (
          <div className="text-muted-foreground text-sm">{description}</div>
        )}
      </header>
      <main className="mt-4">{children}</main>
    </section>
  );
}

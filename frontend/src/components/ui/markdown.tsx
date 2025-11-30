"use client";

import dynamic from "next/dynamic";
import { Skeleton } from "@/components/ui/skeleton";

interface MarkdownProps {
  children: string;
  className?: string;
}

// Dynamically import react-markdown with SSR disabled
const ReactMarkdown = dynamic(
  () => import("react-markdown").then((mod) => mod.default),
  {
    ssr: false,
    loading: () => <Skeleton className="h-4 w-full" />,
  }
);

export function Markdown({ children, className = "" }: MarkdownProps) {
  return (
    <div
      className={`prose prose-sm dark:prose-invert max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-li:my-0 prose-strong:text-foreground ${className}`}
    >
      <ReactMarkdown>{children}</ReactMarkdown>
    </div>
  );
}

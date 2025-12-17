"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownProps {
  content?: string;
  children?: string;
  className?: string;
}

export function Markdown({ content, children, className }: MarkdownProps) {
  const markdownContent = content || children || "";
  return (
    <div className={className}>
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // Style headings
        h1: ({ children }) => (
          <h1 className="text-2xl font-bold mt-6 mb-4 first:mt-0">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-xl font-semibold mt-5 mb-3">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-lg font-medium mt-4 mb-2">{children}</h3>
        ),
        // Style paragraphs
        p: ({ children }) => (
          <p className="my-1 first:mt-0 last:mb-0 leading-relaxed">{children}</p>
        ),
        // Style lists
        ul: ({ children }) => (
          <ul className="list-disc pl-5 my-3 space-y-1 marker:text-current">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal pl-5 my-3 space-y-1 marker:text-current">{children}</ol>
        ),
        // Style code blocks
        code: ({ className, children, ...props }) => {
          const isInline = !className;
          if (isInline) {
            return (
              <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                {children}
              </code>
            );
          }
          return (
            <code className="block bg-muted p-4 rounded-lg text-sm font-mono overflow-x-auto my-3" {...props}>
              {children}
            </code>
          );
        },
        pre: ({ children }) => (
          <pre className="bg-muted rounded-lg overflow-x-auto my-3">{children}</pre>
        ),
        // Style blockquotes
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-primary/30 pl-4 my-3 italic text-muted-foreground">
            {children}
          </blockquote>
        ),
        // Style tables
        table: ({ children }) => (
          <div className="overflow-x-auto my-4">
            <table className="min-w-full border-collapse border border-border">
              {children}
            </table>
          </div>
        ),
        th: ({ children }) => (
          <th className="border border-border bg-muted px-4 py-2 text-left font-semibold">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="border border-border px-4 py-2">{children}</td>
        ),
        // Style links
        a: ({ href, children }) => (
          <a
            href={href}
            className="text-primary underline hover:no-underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            {children}
          </a>
        ),
        // Style horizontal rules
        hr: () => <hr className="my-6 border-border" />,
      }}
    >
      {markdownContent}
    </ReactMarkdown>
    </div>
  );
}

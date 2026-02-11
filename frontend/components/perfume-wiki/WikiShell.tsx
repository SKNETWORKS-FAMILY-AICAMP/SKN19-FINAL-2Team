import type { ReactNode } from "react";

type WikiShellProps = {
  children: ReactNode;
  className?: string;
};

export default function WikiShell({ children, className = "" }: WikiShellProps) {
  return (
    <main
      className={`pt-[108px] sm:pt-[116px] md:pt-[124px] pb-16 sm:pb-24 px-4 sm:px-6 max-w-7xl mx-auto ${className}`}
    >
      {children}
    </main>
  );
}

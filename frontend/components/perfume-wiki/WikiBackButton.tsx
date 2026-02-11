import Link from "next/link";
import { ArrowLeft } from "lucide-react";

type WikiBackButtonProps = {
  href: string;
  label: string;
};

export default function WikiBackButton({ href, label }: WikiBackButtonProps) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-1.5 rounded-full border border-[#E6E0D2] bg-white/90 px-2.5 py-1.5 text-xs sm:px-3 sm:py-2 sm:text-sm font-medium text-[#5A5A5A] hover:text-black hover:border-[#C8A24D] transition-colors"
    >
      <ArrowLeft className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
      <span>{label}</span>
    </Link>
  );
}

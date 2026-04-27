import type { ReactNode } from "react";

export const metadata = {
  title: "Admin — Portfolio",
  robots: { index: false, follow: false },
};

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-50">
      {children}
    </div>
  );
}

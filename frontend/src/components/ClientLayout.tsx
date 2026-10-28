"use client";

import { AuthProvider } from "@/contexts/AuthContext";
import Navbar from "@/components/Navbar";

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  return <AuthProvider>
    <div className="app-background" aria-hidden="true" />
    <Navbar />
    <main id="main-content" className="app-main">{children}</main>
  </AuthProvider>;
}

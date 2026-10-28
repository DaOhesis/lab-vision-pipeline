import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IoT Lab Vision Intelligence | Edge Pipeline",
  description: "Real-time edge computer vision monitoring for laboratory equipment tracking.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased selection:bg-emerald-500 selection:text-black">
        {children}
      </body>
    </html>
  );
}

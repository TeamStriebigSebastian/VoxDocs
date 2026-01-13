import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VoxDocs Pflegedienst",
  description: "Dokumentationssystem für Pflegedienste",
  manifest: "/manifest.json",
  themeColor: "#0ea5e9",
  viewport: {
    width: "device-width",
    initialScale: 1,
    maximumScale: 1,
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "VoxDocs",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de">
      <head>
        <link rel="icon" href="/icon-192x192.png" />
        <link rel="apple-touch-icon" href="/icon-192x192.png" />
      </head>
      <body className="antialiased bg-gray-50">
        {children}
      </body>
    </html>
  );
}

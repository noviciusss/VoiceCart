import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VoiceCart — Voice Command Shopping Assistant",
  description:
    "Add groceries to your list hands-free using voice commands. Powered by Groq AI with English and Hindi support.",
  keywords: ["voice", "shopping list", "grocery", "AI", "voice commands"],
  openGraph: {
    title: "VoiceCart — Voice Command Shopping Assistant",
    description: "Add groceries to your list hands-free using voice commands",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

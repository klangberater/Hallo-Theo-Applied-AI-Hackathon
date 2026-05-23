import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Fletcher — Operations Inbox',
  description: 'KI-Copilot für die WEG-Verwaltung',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body className="min-h-screen bg-paper-50 text-paper-900">{children}</body>
    </html>
  );
}

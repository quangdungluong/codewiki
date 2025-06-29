import { LanguageProvider } from '@/contexts/LanguageContext';
import type { Metadata } from 'next';
import { ThemeProvider } from 'next-themes';
import {
  Geist,
  Geist_Mono,
  Noto_Sans_JP,
  Noto_Serif_JP,
} from 'next/font/google';
import './globals.css';

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

// Japanese-friendly fonts
const notoSansJP = Noto_Sans_JP({
  variable: '--font-geist-sans',
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  display: 'swap',
});

const notoSerifJP = Noto_Serif_JP({
  variable: '--font-serif-jp',
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'codewiki | quangdungluong',
  description: 'Create by quangdungluong',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang='en' suppressHydrationWarning>
      <body
        className={`${notoSansJP.variable} ${notoSerifJP.variable} ${geistMono.variable} antialiased`}
      >
        <ThemeProvider attribute='data-theme' defaultTheme='light' enableSystem>
          <LanguageProvider>{children}</LanguageProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

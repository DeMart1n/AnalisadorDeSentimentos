import type { Metadata } from "next";
import { Inter, Manrope } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/Providers";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const manrope = Manrope({ subsets: ["latin"], variable: "--font-manrope" });

export const metadata: Metadata = {
  title: "SentimentIQ Analytics",
  description: "Análise de sentimentos em atendimentos via chat",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <head>
        <link 
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&amp;display=swap" 
          rel="stylesheet" 
        />
      </head>
      <body className={`${inter.variable} ${manrope.variable} antialiased selection:bg-primary-fixed selection:text-on-primary-fixed`}>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}

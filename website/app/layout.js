import { Inter, Poppins } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })
const poppins = Poppins({ subsets: ['latin'], weight: ['500', '600'], variable: '--font-brand' })

export const metadata = {
  title: 'VeilProof - AI-Powered CAPTCHA',
  description: 'Stop bots without frustrating humans. Invisible behavioral verification powered by machine learning.',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={`${inter.className} ${poppins.variable}`}>{children}</body>
    </html>
  )
}

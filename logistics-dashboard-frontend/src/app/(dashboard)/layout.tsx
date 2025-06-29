'use client' // Required for Chakra UI components and Layout client component

import Layout from '@/components/Layout'; // Using import alias

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <Layout>{children}</Layout>
}

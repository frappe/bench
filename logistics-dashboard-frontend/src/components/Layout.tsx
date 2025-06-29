'use client'

import { Box } from '@chakra-ui/react';
import Header from './Header';
import Sidebar from './Sidebar';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout = ({ children }: LayoutProps) => {
  const sidebarWidth = '250px';
  const headerHeight = '64px'; // Match header height

  return (
    <Box>
      <Header />
      <Sidebar />
      <Box
        as="main"
        pt={headerHeight} // Push content below fixed header
        pl={sidebarWidth} // Push content to the right of fixed sidebar
        height={`calc(100vh - ${headerHeight})`} // Full viewport height minus header
        overflowY="auto" // Scroll main content if it overflows
        p={6} // Some padding for the content area
      >
        {children}
      </Box>
    </Box>
  );
};

export default Layout;

'use client'

import { Box, VStack, Link, Text, Divider } from '@chakra-ui/react';
import NextLink from 'next/link';

const Sidebar = () => {
  const sidebarWidth = '250px';
  const paddingTop = '64px'; // Assuming header height is 64px

  return (
    <Box
      as="nav"
      position="fixed"
      left={0}
      top={paddingTop}
      bottom={0}
      w={sidebarWidth}
      bg="gray.700"
      color="white"
      padding={4}
      zIndex="sticky"
      overflowY="auto"
    >
      <VStack align="stretch" spacing={3}>
        <Text fontSize="xl" fontWeight="bold" mb={4}>Modules</Text>

        <Link as={NextLink} href="/dashboard/warehouse" _hover={{ textDecoration: 'none', bg: 'gray.600' }} p={2} borderRadius="md">
          Warehouse Mgt.
        </Link>
        <Link as={NextLink} href="/dashboard/transport" _hover={{ textDecoration: 'none', bg: 'gray.600' }} p={2} borderRadius="md">
          Transportation Mgt.
        </Link>
        <Link as={NextLink} href="/dashboard/supply-chain" _hover={{ textDecoration: 'none', bg: 'gray.600' }} p={2} borderRadius="md">
          Supply Chain Vis.
        </Link>

        <Divider my={4} />

        {/* Placeholder for future links like User Management for Admin */}
        <Text fontSize="lg" fontWeight="semibold" mt={4}>Admin</Text>
        <Link as={NextLink} href="/admin/user-management" _hover={{ textDecoration: 'none', bg: 'gray.600' }} p={2} borderRadius="md">
          User Management
        </Link>
      </VStack>
    </Box>
  );
};

export default Sidebar;

'use client'

import { Box, Button, Container, Heading, Text, VStack } from '@chakra-ui/react';
import NextLink from 'next/link';

export default function HomePage() {
  return (
    <Container centerContent maxW="container.md" height="100vh" display="flex" flexDirection="column" justifyContent="center" alignItems="center" bg="gray.50">
      <VStack spacing={8} p={10} boxShadow="xl" bg="white" borderRadius="lg">
        <Heading as="h1" size="2xl" color="teal.600">
          Logistics Management System
        </Heading>
        <Text fontSize="xl" color="gray.700">
          Welcome! Please log in to access the dashboard.
        </Text>
        <Box textAlign="center">
          <Text mb={4} fontSize="md" color="gray.600">(Login Form will be here)</Text>
          <Button
            as={NextLink}
            href="/dashboard" // This will route to (dashboard)/page.tsx
            colorScheme="teal"
            size="lg"
            _hover={{ transform: 'translateY(-2px)', boxShadow: 'lg' }}
          >
            Access Dashboard (Dev)
          </Button>
        </Box>
        <Text fontSize="sm" color="gray.500">
          (Registration link will also appear here later)
        </Text>
      </VStack>
      <Text mt={10} fontSize="xs" color="gray.400">
        &copy; {new Date().getFullYear()} Logistics Inc. All rights reserved.
      </Text>
    </Container>
  );
}

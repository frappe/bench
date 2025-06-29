'use client'

import { Heading, Text, VStack } from '@chakra-ui/react';

export default function DashboardHomePage() {
  return (
    <VStack spacing={4} align="stretch">
      <Heading as="h1" size="xl">Welcome to the Logistics Dashboard</Heading>
      <Text fontSize="lg">
        This is the main dashboard area. Select a module from the sidebar to get started.
      </Text>
      <Text>
        Future content will include overview KPIs, alerts, and summaries from various logistics modules.
      </Text>
    </VStack>
  );
}

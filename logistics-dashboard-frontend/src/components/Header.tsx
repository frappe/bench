'use client'

import { Box, Flex, Heading, Spacer, Input, Avatar } from '@chakra-ui/react';

const Header = () => {
  return (
    <Flex
      as="header"
      align="center"
      justify="space-between"
      wrap="wrap"
      padding={4}
      bg="gray.800"
      color="white"
      position="fixed"
      top={0}
      left={0}
      right={0}
      zIndex="banner"
    >
      <Flex align="center" mr={5}>
        <Heading as="h1" size="lg" letterSpacing={'tighter'}>
          Logistics Dashboard
        </Heading>
      </Flex>

      <Box
        display={{ base: 'none', md: 'flex' }}
        width={{ base: 'full', md: 'auto' }}
        alignItems="center"
        flexGrow={1}
        ml={10}
      >
        <Input
          placeholder="Global Search..."
          variant="filled"
          bg="gray.700"
          color="white"
          _hover={{ bg: 'gray.600' }}
          _focus={{ bg: 'gray.600', borderColor: 'teal.300' }}
          maxWidth="400px"
        />
      </Box>

      <Spacer />

      <Box>
        {/* User Profile - Placeholder */}
        <Avatar name="User Name" src="" size="sm" />
        {/* <Text ml={2} display={{ base: 'none', md: 'inline' }}>User Name</Text> */}
      </Box>
    </Flex>
  );
};

export default Header;

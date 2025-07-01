require('dotenv').config();
const { generateToken } = require('phlow-auth');

async function testBasicAgent() {
  console.log('🧪 Testing Basic Agent...\n');

  const baseUrl = `http://localhost:${process.env.PORT || 3000}`;
  
  try {
    // Test 1: Health check
    console.log('1. Testing health endpoint...');
    const healthResponse = await fetch(`${baseUrl}/health`);
    const healthData = await healthResponse.json();
    console.log('✅ Health check:', healthData.status);

    // Test 2: Public endpoint
    console.log('\n2. Testing public endpoint...');
    const publicResponse = await fetch(baseUrl);
    const publicData = await publicResponse.json();
    console.log('✅ Public endpoint accessible');
    console.log('   Agent:', publicData.agent.name);

    // Test 3: Protected endpoint without token (should fail)
    console.log('\n3. Testing protected endpoint without token...');
    const unprotectedResponse = await fetch(`${baseUrl}/protected`);
    if (unprotectedResponse.status === 401) {
      console.log('✅ Protected endpoint correctly rejected unauthorized request');
    } else {
      console.log('❌ Protected endpoint should have rejected unauthorized request');
    }

    // Test 4: Generate test token and access protected endpoint
    if (process.env.AGENT_PRIVATE_KEY && process.env.AGENT_ID) {
      console.log('\n4. Testing protected endpoint with valid token...');
      
      const testAgent = {
        agentId: 'test-client-agent',
        name: 'Test Client Agent',
        permissions: ['read:data', 'write:data'],
        publicKey: process.env.AGENT_PUBLIC_KEY.replace(/\\n/g, '\n'),
      };

      const token = generateToken(
        testAgent,
        process.env.AGENT_PRIVATE_KEY.replace(/\\n/g, '\n'),
        process.env.AGENT_ID,
        '1h'
      );

      const protectedResponse = await fetch(`${baseUrl}/protected`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'X-Phlow-Agent-Id': 'test-client-agent',
          'Content-Type': 'application/json',
        },
      });

      if (protectedResponse.ok) {
        const protectedData = await protectedResponse.json();
        console.log('✅ Protected endpoint accessible with valid token');
        console.log('   Requesting agent:', protectedData.requestingAgent.name);
      } else {
        const errorData = await protectedResponse.json();
        console.log('❌ Protected endpoint failed:', errorData.message);
      }

      // Test 5: Test data endpoint with read permission
      console.log('\n5. Testing data endpoint with read permission...');
      const dataResponse = await fetch(`${baseUrl}/data`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'X-Phlow-Agent-Id': 'test-client-agent',
        },
      });

      if (dataResponse.ok) {
        console.log('✅ Data endpoint accessible with read permission');
      } else {
        const errorData = await dataResponse.json();
        console.log('❌ Data endpoint failed:', errorData.message);
      }

      // Test 6: Test admin endpoint (should fail without admin permission)
      console.log('\n6. Testing admin endpoint without admin permission...');
      const adminResponse = await fetch(`${baseUrl}/admin`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'X-Phlow-Agent-Id': 'test-client-agent',
        },
      });

      if (adminResponse.status === 403) {
        console.log('✅ Admin endpoint correctly rejected insufficient permissions');
      } else {
        console.log('❌ Admin endpoint should have rejected insufficient permissions');
      }
    } else {
      console.log('\n⚠️  Skipping token tests - missing AGENT_PRIVATE_KEY or AGENT_ID');
    }

    console.log('\n🎉 Basic agent testing completed!');

  } catch (error) {
    console.error('❌ Test failed:', error.message);
    process.exit(1);
  }
}

// Check if server is running
async function checkServer() {
  const baseUrl = `http://localhost:${process.env.PORT || 3000}`;
  try {
    await fetch(`${baseUrl}/health`);
    return true;
  } catch {
    return false;
  }
}

async function main() {
  const serverRunning = await checkServer();
  
  if (!serverRunning) {
    console.log('❌ Server not running. Please start the agent first:');
    console.log('   npm start');
    process.exit(1);
  }

  await testBasicAgent();
}

main();
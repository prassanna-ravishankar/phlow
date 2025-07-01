#!/usr/bin/env node

/**
 * Simple test script for the multi-agent network example
 * This would typically run integration tests against the network
 */

console.log('🧪 Testing multi-agent network...');

// For now, just verify the main files exist
const fs = require('fs');
const path = require('path');

const requiredFiles = [
  'coordinator.js',
  'agents/data-agent.js',
  'agents/auth-agent.js',
  'agents/compute-agent.js'
];

let allFilesExist = true;

requiredFiles.forEach(file => {
  const filePath = path.join(__dirname, file);
  if (fs.existsSync(filePath)) {
    console.log(`✅ ${file} exists`);
  } else {
    console.log(`❌ ${file} missing`);
    allFilesExist = false;
  }
});

if (allFilesExist) {
  console.log('✅ All required files present');
  console.log('🎉 Multi-agent network test passed');
  process.exit(0);
} else {
  console.log('❌ Some required files are missing');
  process.exit(1);
}
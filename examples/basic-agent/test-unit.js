#!/usr/bin/env node

/**
 * Unit tests for the basic agent example
 * These tests don't require the server to be running
 */

console.log('🧪 Testing basic agent (unit tests)...');

const fs = require('fs');
const path = require('path');

// Test 1: Check required files exist
console.log('1. Checking required files...');
const requiredFiles = ['index.js', 'package.json', 'README.md'];
let allFilesExist = true;

requiredFiles.forEach(file => {
  const filePath = path.join(__dirname, file);
  if (fs.existsSync(filePath)) {
    console.log(`   ✅ ${file} exists`);
  } else {
    console.log(`   ❌ ${file} missing`);
    allFilesExist = false;
  }
});

// Test 2: Check if phlow-auth can be imported
console.log('\n2. Testing phlow-auth import...');
try {
  const { generateToken, verify_token } = require('phlow-auth');
  console.log('   ✅ phlow-auth imported successfully');
  
  // Test that functions exist
  if (typeof generateToken === 'function') {
    console.log('   ✅ generateToken function available');
  } else {
    console.log('   ❌ generateToken function missing');
    allFilesExist = false;
  }
} catch (error) {
  console.log(`   ❌ Failed to import phlow-auth: ${error.message}`);
  allFilesExist = false;
}

// Test 3: Check if main index.js has basic structure
console.log('\n3. Checking index.js structure...');
try {
  const indexContent = fs.readFileSync(path.join(__dirname, 'index.js'), 'utf8');
  
  if (indexContent.includes('express')) {
    console.log('   ✅ Uses Express framework');
  } else {
    console.log('   ❌ Express framework not found');
  }
  
  if (indexContent.includes('phlow-auth') || indexContent.includes('PhlowMiddleware')) {
    console.log('   ✅ Uses Phlow authentication');
  } else {
    console.log('   ❌ Phlow authentication not found');
  }
  
} catch (error) {
  console.log(`   ❌ Failed to read index.js: ${error.message}`);
  allFilesExist = false;
}

if (allFilesExist) {
  console.log('\n🎉 Basic agent unit tests passed');
  process.exit(0);
} else {
  console.log('\n❌ Some unit tests failed');
  process.exit(1);
}
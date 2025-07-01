import forge from 'node-forge';

export function generateKeyPair(): { publicKey: string; privateKey: string } {
  const { publicKey, privateKey } = forge.pki.rsa.generateKeyPair(2048);
  
  return {
    publicKey: forge.pki.publicKeyToPem(publicKey),
    privateKey: forge.pki.privateKeyToPem(privateKey),
  };
}

export function validateKeyPair(publicKey: string, privateKey: string): boolean {
  try {
    const pubKey = forge.pki.publicKeyFromPem(publicKey);
    const privKey = forge.pki.privateKeyFromPem(privateKey);
    
    const testMessage = 'test-message';
    const md = forge.md.sha256.create();
    md.update(testMessage);
    const signature = privKey.sign(md);
    
    const verifyMd = forge.md.sha256.create();
    verifyMd.update(testMessage);
    return pubKey.verify(verifyMd.digest().bytes(), signature);
  } catch {
    return false;
  }
}
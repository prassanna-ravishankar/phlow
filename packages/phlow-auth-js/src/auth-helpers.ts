import * as jwt from 'jsonwebtoken';
import { AgentCard } from './types';

/**
 * Generate a JWT token for an agent
 */
export function generateToken(agentCard: AgentCard, privateKey: string): string {
  const payload = {
    sub: agentCard.metadata?.agentId,
    name: agentCard.name,
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + (60 * 60), // 1 hour
  };

  return jwt.sign(payload, privateKey, { algorithm: 'HS256' });
}

/**
 * Verify a JWT token (legacy naming for compatibility)
 */
export function verify_token(token: string, publicKey: string): jwt.JwtPayload | string {
  return jwt.verify(token, publicKey);
}

/**
 * Verify a JWT token (modern naming)
 */
export function verifyToken(token: string, publicKey: string): jwt.JwtPayload | string {
  return verify_token(token, publicKey);
}
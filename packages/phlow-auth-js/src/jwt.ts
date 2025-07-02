import jwt from 'jsonwebtoken';
import { AgentCard, JWTClaims } from './types';
import { AuthenticationError } from './errors';

export function generateToken(
  agentCard: AgentCard,
  privateKey: string,
  audience: string,
  expiresIn: string = '1h'
): string {
  const claims: JWTClaims = {
    sub: agentCard.agentId,
    iss: agentCard.agentId,
    aud: audience,
    exp: Math.floor(Date.now() / 1000) + parseExpiry(expiresIn),
    iat: Math.floor(Date.now() / 1000),
    skills: agentCard.skills?.map(s => s.name),
    metadata: agentCard.metadata,
  };

  return jwt.sign(claims, privateKey, {
    algorithm: 'RS256',
  });
}

export function verifyToken(
  token: string,
  publicKey: string,
  options?: {
    audience?: string;
    issuer?: string;
  }
): JWTClaims {
  try {
    const decoded = jwt.verify(token, publicKey, {
      algorithms: ['RS256'],
      audience: options?.audience,
      issuer: options?.issuer,
    }) as JWTClaims;

    return decoded;
  } catch (error: any) {
    if (error.name === 'TokenExpiredError') {
      throw new AuthenticationError('Token has expired', 'TOKEN_EXPIRED');
    } else if (error.name === 'JsonWebTokenError') {
      throw new AuthenticationError('Invalid token', 'TOKEN_INVALID');
    } else {
      throw new AuthenticationError(`Token verification failed: ${error.message}`, 'TOKEN_VERIFY_FAILED');
    }
  }
}

export function decodeToken(token: string): JWTClaims | null {
  try {
    const decoded = jwt.decode(token) as JWTClaims;
    return decoded;
  } catch {
    return null;
  }
}


function parseExpiry(expiry: string): number {
  const match = expiry.match(/^(\d+)([smhd])$/);
  if (!match) {
    throw new Error(`Invalid expiry format: ${expiry}`);
  }

  const [, value, unit] = match;
  const num = parseInt(value, 10);

  switch (unit) {
    case 's':
      return num;
    case 'm':
      return num * 60;
    case 'h':
      return num * 60 * 60;
    case 'd':
      return num * 60 * 60 * 24;
    default:
      throw new Error(`Invalid expiry unit: ${unit}`);
  }
}
import jwt from 'jsonwebtoken';
import { AgentCard, JWTClaims, TokenPair } from './types';
import { TokenError } from './errors';

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
    permissions: agentCard.permissions,
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
    ignoreExpiration?: boolean;
  }
): JWTClaims {
  try {
    const decoded = jwt.verify(token, publicKey, {
      algorithms: ['RS256'],
      audience: options?.audience,
      issuer: options?.issuer,
      ignoreExpiration: options?.ignoreExpiration,
    }) as JWTClaims;

    return decoded;
  } catch (error: any) {
    if (error.name === 'TokenExpiredError') {
      throw new TokenError('Token has expired', 'TOKEN_EXPIRED');
    } else if (error.name === 'JsonWebTokenError') {
      throw new TokenError('Invalid token', 'TOKEN_INVALID');
    } else {
      throw new TokenError(`Token verification failed: ${error.message}`, 'TOKEN_VERIFY_FAILED');
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

export function generateTokenPair(
  agentCard: AgentCard,
  privateKey: string,
  audience: string,
  accessExpiresIn: string = '1h',
  refreshExpiresIn: string = '7d'
): TokenPair {
  const accessToken = generateToken(agentCard, privateKey, audience, accessExpiresIn);
  const refreshToken = generateToken(agentCard, privateKey, audience, refreshExpiresIn);

  return {
    accessToken,
    refreshToken,
  };
}

export function isTokenExpired(token: string, thresholdSeconds: number = 0): boolean {
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) {
    return true;
  }

  const now = Math.floor(Date.now() / 1000);
  return decoded.exp - now <= thresholdSeconds;
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
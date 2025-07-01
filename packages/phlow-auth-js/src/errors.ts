export class PhlowError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode: number = 500
  ) {
    super(message);
    this.name = 'PhlowError';
  }
}

export class AuthenticationError extends PhlowError {
  constructor(message: string, code: string = 'AUTH_ERROR') {
    super(message, code, 401);
    this.name = 'AuthenticationError';
  }
}

export class AuthorizationError extends PhlowError {
  constructor(message: string, code: string = 'AUTHZ_ERROR') {
    super(message, code, 403);
    this.name = 'AuthorizationError';
  }
}

export class ConfigurationError extends PhlowError {
  constructor(message: string, code: string = 'CONFIG_ERROR') {
    super(message, code, 500);
    this.name = 'ConfigurationError';
  }
}

export class TokenError extends PhlowError {
  constructor(message: string, code: string = 'TOKEN_ERROR') {
    super(message, code, 401);
    this.name = 'TokenError';
  }
}

export class RateLimitError extends PhlowError {
  constructor(message: string = 'Rate limit exceeded', code: string = 'RATE_LIMIT') {
    super(message, code, 429);
    this.name = 'RateLimitError';
  }
}
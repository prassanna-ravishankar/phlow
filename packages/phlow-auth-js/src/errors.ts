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

export class ConfigurationError extends PhlowError {
  constructor(message: string, code: string = 'CONFIG_ERROR') {
    super(message, code, 500);
    this.name = 'ConfigurationError';
  }
}
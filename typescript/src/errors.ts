/** Errors, one class per HTTP status class, all carrying the platform's error envelope. */

export interface ErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
    retryable?: boolean;
    trace_id?: string;
  };
  detail?: unknown;
}

export class MembaseError extends Error {
  readonly status: number | undefined;
  readonly body: unknown;
  readonly code: string;
  readonly details: unknown;
  readonly retryable: boolean;
  readonly traceId: string;

  constructor(message: string, opts: { status?: number; body?: unknown } = {}) {
    super(message);
    this.name = new.target.name;
    this.status = opts.status;
    this.body = opts.body;
    const err = (opts.body as ErrorEnvelope | undefined)?.error ?? {};
    this.code = String(err.code ?? "");
    this.details = err.details;
    this.retryable = Boolean(err.retryable ?? false);
    this.traceId = String(err.trace_id ?? "");
  }
}

/** The request never got an answer (DNS, connection refused, reset). */
export class APIConnectionError extends MembaseError {}
/** The request ran past the client's timeout. */
export class APITimeoutError extends APIConnectionError {}

/** A non-2xx answer. */
export class APIStatusError extends MembaseError {}
/** 400 — a malformed request: a missing `q`, both `content` and `url`, an ambiguous `container`. */
export class BadRequestError extends APIStatusError {}
/** 401 — the request carried no bearer at all. */
export class AuthenticationError extends APIStatusError {}
/** 403 (`code: unauthorized`) — an unknown, expired or revoked key; a container outside the key's reach; or a verb above its access level. */
export class PermissionDeniedError extends APIStatusError {}
/** 404 — an unknown document or memory id. */
export class NotFoundError extends APIStatusError {}
/** 409. */
export class ConflictError extends APIStatusError {}
/** 422 — the account's memory cannot run a turn on this deployment (`capability_unavailable`). */
export class UnprocessableEntityError extends APIStatusError {}
/** 429 — the account's turn budget is spent for now. */
export class RateLimitError extends APIStatusError {}
/** 5xx. */
export class InternalServerError extends APIStatusError {}

const BY_STATUS: Record<number, new (m: string, o: { status?: number; body?: unknown }) => APIStatusError> = {
  400: BadRequestError,
  401: AuthenticationError,
  403: PermissionDeniedError,
  404: NotFoundError,
  409: ConflictError,
  422: UnprocessableEntityError,
  429: RateLimitError,
};

/** The exception for a non-2xx answer. */
export function errorFor(status: number, body: unknown, fallback = ""): APIStatusError {
  const env = (body ?? {}) as ErrorEnvelope;
  let message = env.error?.message;
  if (!message && env.detail !== undefined) message = typeof env.detail === "string" ? env.detail : JSON.stringify(env.detail);
  message = message || fallback || `HTTP ${status}`;
  const Cls = BY_STATUS[status] ?? (status >= 500 ? InternalServerError : APIStatusError);
  return new Cls(message, { status, body });
}

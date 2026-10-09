import { computeSignature, verifySignature } from './signature';
import {
  AttributionParams,
  AttributionResult,
  ClientConfig,
  CreditBalance,
  CreditReservationParams,
  CreditReservationResult,
  EventEnvelope,
} from './types';

export class ReferralClient {
  private baseUrl: string;
  private keyId: string;
  private secret: string;
  private signingSecret: string;
  private timeoutMs: number;
  private maxRetries: number;

  constructor(config: ClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/+$/, '');
    this.keyId = config.keyId;
    this.secret = config.secret;
    this.signingSecret = config.signingSecret;
    this.timeoutMs = config.timeoutMs ?? 10000;
    this.maxRetries = config.maxRetries ?? 3;
  }

  private get authHeader(): string {
    return `Bearer ${this.keyId}.${this.secret}`;
  }

  private async requestWithRetry(
    method: string,
    path: string,
    body?: string,
    extraHeaders?: Record<string, string>
  ): Promise<Response> {
    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {
      Authorization: this.authHeader,
      'Content-Type': 'application/json',
      ...extraHeaders,
    };

    let lastError: Error | null = null;
    for (let attempt = 0; attempt < this.maxRetries; attempt++) {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), this.timeoutMs);
        const resp = await fetch(url, {
          method,
          headers,
          body,
          signal: controller.signal,
        });
        clearTimeout(timeout);

        if (resp.status >= 500 && attempt < this.maxRetries - 1) {
          await new Promise((r) => setTimeout(r, 100 * Math.pow(2, attempt)));
          continue;
        }

        if (!resp.ok) {
          const errText = await resp.text();
          throw new Error(`Platform error (${resp.status}): ${errText}`);
        }

        return resp;
      } catch (err: unknown) {
        lastError = err instanceof Error ? err : new Error(String(err));
        if (attempt < this.maxRetries - 1) {
          await new Promise((r) => setTimeout(r, 100 * Math.pow(2, attempt)));
          continue;
        }
      }
    }

    throw lastError ?? new Error('Request failed after max retries');
  }

  async attribute(params: AttributionParams, failSoft = true): Promise<AttributionResult | null> {
    const regDate = params.registeredAt instanceof Date ? params.registeredAt.toISOString() : params.registeredAt;
    const body = JSON.stringify({
      external_user_id: params.externalUserId,
      registered_at: regDate,
      referral_code: params.referralCode,
      attribution_token: params.attributionToken,
      signals: params.signals,
    });

    try {
      const resp = await this.requestWithRetry('POST', '/v1/attributions', body);
      return (await resp.json()) as AttributionResult;
    } catch (err) {
      if (failSoft) {
        return null;
      }
      throw err;
    }
  }

  async sendEvent(event: EventEnvelope): Promise<{ accepted: boolean; event_id: string }> {
    const eventId = event.event_id || `evt_${Math.random().toString(36).substring(2, 15)}`;
    const occurredAt = event.occurred_at || new Date().toISOString();
    const payload = {
      event_id: eventId,
      event_type: event.event_type,
      schema_version: event.schema_version ?? 1,
      occurred_at: occurredAt,
      data: event.data,
    };
    const rawBody = JSON.stringify(payload);
    const timestamp = Math.floor(Date.now() / 1000);
    const signature = computeSignature(this.signingSecret, timestamp, rawBody);

    const resp = await this.requestWithRetry('POST', '/v1/events', rawBody, {
      'X-Signature-Timestamp': String(timestamp),
      'X-Signature': signature,
    });

    return (await resp.json()) as { accepted: boolean; event_id: string };
  }

  async getCreditBalance(externalUserId: string, currency = 'BDT'): Promise<CreditBalance> {
    const resp = await this.requestWithRetry(
      'GET',
      `/v1/credits/balance?external_user_id=${encodeURIComponent(externalUserId)}&currency=${encodeURIComponent(currency)}`
    );
    return (await resp.json()) as CreditBalance;
  }

  async reserveCredit(params: CreditReservationParams): Promise<CreditReservationResult> {
    const idempotencyKey = params.idempotencyKey || `resv_${Math.random().toString(36).substring(2, 15)}`;
    const body = JSON.stringify({
      external_user_id: params.externalUserId,
      requested_amount: params.requestedAmount,
      order_ref: params.orderRef,
      idempotency_key: idempotencyKey,
      currency: params.currency || 'BDT',
    });
    const resp = await this.requestWithRetry('POST', '/v1/credits/reservations', body);
    return (await resp.json()) as CreditReservationResult;
  }

  async captureCredit(reservationId: string, amountMinor?: number, paymentId?: string): Promise<{ state: string }> {
    const body = JSON.stringify({ amount_minor: amountMinor, payment_id: paymentId });
    const resp = await this.requestWithRetry('POST', `/v1/credits/reservations/${reservationId}/capture`, body);
    return (await resp.json()) as { state: string };
  }

  async releaseCredit(reservationId: string): Promise<{ state: string }> {
    const resp = await this.requestWithRetry('POST', `/v1/credits/reservations/${reservationId}/release`);
    return (await resp.json()) as { state: string };
  }
}

export * from './signature';
export * from './types';

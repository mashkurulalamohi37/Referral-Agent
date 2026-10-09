import * as crypto from 'crypto';

export function computeSignature(signingSecret: string, timestamp: number, rawBody: string | Buffer): string {
  const bodyBuf = typeof rawBody === 'string' ? Buffer.from(rawBody, 'utf8') : rawBody;
  const message = Buffer.concat([Buffer.from(`${timestamp}.`, 'utf8'), bodyBuf]);
  const hmac = crypto.createHmac('sha256', signingSecret);
  hmac.update(message);
  const digest = hmac.digest('hex');
  return `v1=${digest}`;
}

export function verifySignature(
  signingSecret: string,
  timestamp: number,
  rawBody: string | Buffer,
  signatureHeader: string,
  toleranceSeconds = 300
): boolean {
  const currentTime = Math.floor(Date.now() / 1000);
  if (Math.abs(currentTime - timestamp) > toleranceSeconds) {
    return false;
  }
  const expectedSig = computeSignature(signingSecret, timestamp, rawBody);
  return crypto.timingSafeEqual(Buffer.from(expectedSig), Buffer.from(signatureHeader));
}

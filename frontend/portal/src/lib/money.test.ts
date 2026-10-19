import { describe, expect, it } from 'vitest';
import { applyBps, formatMoney, parseMoney, toMajorString } from './money';

describe('toMajorString', () => {
  it.each([
    [20000, '200.00'],
    [5, '0.05'],
    [0, '0.00'],
    [-150, '-1.50'],
    [123456789012345, '1234567890123.45'],
  ])('%i → %s', (minor, expected) => {
    expect(toMajorString(minor, 'BDT')).toBe(expected);
  });

  it('handles zero-decimal currencies', () => {
    expect(toMajorString(1234, 'JPY')).toBe('1234');
  });

  it('rejects non-integers', () => {
    expect(() => toMajorString(1.5, 'BDT')).toThrow();
  });
});

describe('formatMoney', () => {
  it('formats taka with grouping and two decimals', () => {
    expect(formatMoney(150050, 'BDT', { locale: 'en-US' })).toBe('৳1,500.50');
  });

  it('drops a zero fraction when asked', () => {
    expect(formatMoney(150000, 'BDT', { locale: 'en-US', compactZeroFraction: true })).toBe('৳1,500');
    expect(formatMoney(150050, 'BDT', { locale: 'en-US', compactZeroFraction: true })).toBe('৳1,500.50');
  });

  it('shows a sign for earnings rows', () => {
    expect(formatMoney(20000, 'BDT', { locale: 'en-US', signed: true })).toBe('+৳200.00');
    expect(formatMoney(-20000, 'BDT', { locale: 'en-US', signed: true })).toBe('-৳200.00');
  });

  it('keeps precision beyond float range for display', () => {
    expect(formatMoney(900719925474099, 'BDT', { locale: 'en-US' })).toBe('৳9,007,199,254,740.99');
  });
});

describe('parseMoney', () => {
  it.each([
    ['1500', 150000],
    ['1,500.5', 150050],
    ['1500.05', 150005],
    ['  ৳ 2,000 ', 200000],
    ['0.01', 1],
    ['১৫০০', 150000],
    ['1000.29', 100029],
  ])('%s → %i minor', (input, expected) => {
    expect(parseMoney(input, 'BDT')).toEqual({ ok: true, minor: expected });
  });

  it('never goes through floats (1000.29 × 100 would be 100028.99999)', () => {
    expect(parseMoney('1000.29')).toEqual({ ok: true, minor: 100029 });
  });

  it.each([
    ['', 'empty'],
    ['abc', 'invalid'],
    ['1.2.3', 'invalid'],
    ['-5', 'invalid'],
    ['1.001', 'too_many_decimals'],
    ['99999999999999999', 'too_large'],
  ])('rejects %j (%s)', (input, reason) => {
    expect(parseMoney(input, 'BDT')).toEqual({ ok: false, reason });
  });
});

describe('applyBps', () => {
  it('matches the acceptance scenario (৳2,000 at 10% = ৳200)', () => {
    expect(applyBps(200000, 1000)).toBe(20000);
  });

  it('rounds half up', () => {
    expect(applyBps(5, 1000)).toBe(1);
    expect(applyBps(4, 1000)).toBe(0);
    expect(applyBps(-5, 1000)).toBe(-1);
  });
});

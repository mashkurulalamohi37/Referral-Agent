import { describe, expect, it } from 'vitest';
import { contrast, ensureContrast } from './theme';

describe('contrast', () => {
  it('matches known WCAG values', () => {
    expect(contrast('#000000', '#ffffff')).toBeCloseTo(21, 0);
    expect(contrast('#ffffff', '#ffffff')).toBeCloseTo(1, 5);
  });
});

describe('ensureContrast', () => {
  it('darkens a pale brand colour until it is AA on white', () => {
    const fixed = ensureContrast('#7dd3fc', '#ffffff');
    expect(contrast(fixed, '#ffffff')).toBeGreaterThanOrEqual(4.5);
  });

  it('lightens a dark brand colour until it is AA on the dark surface', () => {
    const fixed = ensureContrast('#3730a3', '#121826');
    expect(contrast(fixed, '#121826')).toBeGreaterThanOrEqual(4.5);
  });

  it('leaves an already accessible colour unchanged', () => {
    expect(ensureContrast('#4338ca', '#ffffff')).toBe('#4338ca');
  });
});

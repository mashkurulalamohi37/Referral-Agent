import React, { createContext, useContext, useEffect, useState } from 'react';

export interface ProductTheme {
  primaryColor?: string;
  brandName?: string;
  logoUrl?: string;
  accentColor?: string;
}

interface ThemeContextType {
  theme: ProductTheme;
  productSlug: string;
  setProductSlug: (slug: string) => void;
}

const defaultTheme: ProductTheme = {
  primaryColor: '#6366f1',
  brandName: 'Partner Program',
  accentColor: '#10b981',
};

const ThemeContext = createContext<ThemeContextType>({
  theme: defaultTheme,
  productSlug: 'default',
  setProductSlug: () => {},
});

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [productSlug, setProductSlug] = useState<string>('default');
  const [theme, setTheme] = useState<ProductTheme>(defaultTheme);

  useEffect(() => {
    // Check URL parameters for product branding context (e.g. ?product=healora or ?product=pulsepos)
    const params = new URLSearchParams(window.location.search);
    const p = params.get('product');
    if (p) {
      setProductSlug(p);
      if (p === 'healora') {
        setTheme({
          primaryColor: '#0ea5e9',
          brandName: 'Healora Health Referrals',
          accentColor: '#14b8a6',
        });
      } else if (p === 'pulsepos') {
        setTheme({
          primaryColor: '#f97316',
          brandName: 'PulsePOS Partner Hub',
          accentColor: '#eab308',
        });
      }
    }
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, productSlug, setProductSlug }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => useContext(ThemeContext);

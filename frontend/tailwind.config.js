/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)'
      },
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))'
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))'
        },
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))'
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))'
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))'
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))'
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))'
        },
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        chart: {
          '1': 'hsl(var(--chart-1))',
          '2': 'hsl(var(--chart-2))',
          '3': 'hsl(var(--chart-3))',
          '4': 'hsl(var(--chart-4))',
          '5': 'hsl(var(--chart-5))'
        },
        // ── OraOne VDS v1 semantic tokens (mirror src/constants/tokens.js) ──
        brand: {
          DEFAULT: '#2563EB',
          hover: '#1D4ED8',
          soft: '#EFF4FF',
        },
        ink: '#0F172A',
        body: '#334155',
        sub: '#64748B',
        faint: '#94A3B8',
        line: '#EAF0F6',
        hairline: '#F1F5F9',
        stroke: '#E2E8F0',
        canvas: '#F6F8FC',
        subtle: '#FBFCFE',
        wash: '#F8FAFC',
        success: {
          DEFAULT: '#16A34A',
          soft: '#ECFDF3',
          ink: '#067647',
        },
        warning: {
          DEFAULT: '#F59E0B',
          soft: '#FFF7ED',
          ink: '#B45309',
        },
        danger: {
          DEFAULT: '#B42318',
          soft: '#FEF3F2',
          border: '#FEE4E2',
        },
      },
      boxShadow: {
        card: '0 1px 2px rgba(16,24,40,0.04)',
        cardhover: '0 8px 24px -12px rgba(16,24,40,0.16)',
        pop: '0 12px 32px -12px rgba(16,24,40,0.24)',
      },
      keyframes: {
        'accordion-down': {
          from: {
            height: '0'
          },
          to: {
            height: 'var(--radix-accordion-content-height)'
          }
        },
        'accordion-up': {
          from: {
            height: 'var(--radix-accordion-content-height)'
          },
          to: {
            height: '0'
          }
        },
        'slideIn': {
          from: { transform: 'translateX(100%)' },
          to: { transform: 'translateX(0)' }
        }
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'slideIn': 'slideIn 0.2s ease-out'
      }
    }
  },
  plugins: [require("tailwindcss-animate")],
};
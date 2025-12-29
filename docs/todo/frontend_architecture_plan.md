# Frontend Architecture Plan for Lotto Predictore

## Business Decision Analysis

### Personal Use (Recommended Start)
**Pros:**
- No legal/compliance overhead (gambling regulations vary by region)
- No payment processing complexity
- No customer support burden
- Faster to build and iterate
- Test product-market fit privately

**Cons:**
- No revenue stream
- Limited validation of real-world value

### Business Model (Future Consideration)
**Requirements if you go business:**
- Legal consultation (gambling/prediction services regulations)
- Payment processing (Stripe/PayPal)
- User authentication & management
- Subscription tiers
- Terms of service / disclaimers
- Customer support system
- Marketing infrastructure
- Data privacy compliance (GDPR, etc.)

**Recommendation:** Start personal, validate ROI, then consider business if:
1. You're consistently beating random chance
2. You have 3-6 months of positive ROI data
3. You understand local legal requirements
4. You have time for customer support

---

## Frontend Needs Analysis

Based on backend API analysis, the frontend needs:

### Core Features (Personal Use)
1. **Dashboard**
   - Latest predictions display
   - Current week's combinations
   - Quick stats (ROI, recent performance)

2. **Predictions View**
   - List of generated combinations
   - Algorithm used for each prediction
   - Historical predictions with results

3. **Performance Tracking**
   - ROI over time (charts)
   - Algorithm comparison
   - Prize/cost tracking
   - Win rate statistics

4. **Draw History**
   - Historical draws visualization
   - Filter by date range
   - Draw statistics

5. **Manual Controls**
   - Trigger combination generation
   - Trigger draw fetching
   - View cron job status

6. **Simulation Interface**
   - Test algorithms with date ranges
   - Compare algorithm performance
   - View simulation results

### Advanced Features (If Business)
- User authentication
- Subscription management
- Email preferences
- Payment history
- Admin panel

---

## Technology Stack Recommendation

### Recommended: Next.js 14+ (App Router) with TypeScript

**Why Next.js:**
- **Scalability**: Easy to add business features later (auth, payments)
- **Performance**: Server-side rendering for fast initial load
- **Mobile-first**: Built-in responsive design support
- **API Integration**: Easy FastAPI integration
- **Future-proof**: Can add SSR/SSG for public pages if business
- **Type Safety**: TypeScript prevents errors

**Alternative Options:**
- **React + Vite**: Lighter weight, good for personal use only
- **Vue 3 + Nuxt**: If you prefer Vue ecosystem
- **SvelteKit**: Modern, fast, but smaller ecosystem

### Supporting Stack

**UI Framework:**
- **Tailwind CSS** (recommended) - Mobile-first, utility-first, matches your preference
- Alternative: **shadcn/ui** (built on Tailwind) for pre-built components

**State Management:**
- **React Query (TanStack Query)** - For API data fetching/caching
- **Zustand** - Lightweight global state (if needed)

**Charts/Visualization:**
- **Recharts** or **Chart.js** - For ROI/performance charts

**API Client:**
- **Axios** or **fetch** with React Query

**Form Handling:**
- **React Hook Form** - For simulation controls

---

## Architecture Overview

```
Frontend Structure:
├── app/                    # Next.js App Router
│   ├── (dashboard)/        # Dashboard routes
│   │   ├── page.tsx        # Main dashboard
│   │   ├── predictions/   # Predictions view
│   │   ├── performance/    # Performance charts
│   │   └── draws/          # Draw history
│   ├── api/                # API route handlers (if needed)
│   ├── components/         # Reusable components
│   │   ├── ui/             # Base UI components
│   │   ├── charts/         # Chart components
│   │   └── forms/          # Form components
│   ├── lib/                # Utilities
│   │   ├── api.ts          # API client
│   │   └── utils.ts        # Helper functions
│   └── layout.tsx          # Root layout
└── public/                 # Static assets
```

---

## Key API Endpoints to Integrate

Based on backend analysis:

1. **GET /generate-combinations** - Get latest predictions
2. **GET /simulate** - Run algorithm simulations
3. **GET /cron/status** - Check job status
4. **POST /cron/generate-weekly-combinations-optimized** - Trigger generation
5. **GET /cron/prediction-balance-status** - Model balance stats
6. **POST /cron/fetch-latest-draw** - Fetch new draws

---

## Implementation Phases

### Phase 1: MVP (Personal Use)
1. Dashboard with latest predictions
2. Simple performance metrics
3. Manual trigger buttons
4. Basic draw history

**Time Estimate:** 2-3 days

### Phase 2: Enhanced Features
1. Performance charts (ROI over time)
2. Algorithm comparison view
3. Simulation interface
4. Job status monitoring

**Time Estimate:** 3-5 days

### Phase 3: Business Features (If Needed)
1. User authentication
2. Subscription management
3. Email preferences
4. Admin panel

**Time Estimate:** 1-2 weeks

---

## Design Considerations

1. **Mobile-first**: All components responsive
2. **Dark mode**: Consider adding (popular feature)
3. **Real-time updates**: WebSocket or polling for job status
4. **Error handling**: Clear error messages for API failures
5. **Loading states**: Skeleton loaders for better UX

---

## File Structure Example

```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                    # Dashboard
│   ├── predictions/
│   │   ├── page.tsx                # Predictions list
│   │   └── [id]/page.tsx           # Single prediction
│   ├── performance/
│   │   └── page.tsx                # Performance charts
│   ├── draws/
│   │   └── page.tsx                # Draw history
│   └── simulate/
│       └── page.tsx                # Simulation interface
├── components/
│   ├── ui/
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   └── Table.tsx
│   ├── charts/
│   │   └── ROITrendChart.tsx
│   └── forms/
│       └── SimulationForm.tsx
├── lib/
│   ├── api/
│   │   ├── client.ts               # Axios instance
│   │   ├── predictions.ts          # Prediction endpoints
│   │   ├── simulations.ts          # Simulation endpoints
│   │   └── cron.ts                 # Cron endpoints
│   └── hooks/
│       ├── usePredictions.ts      # React Query hooks
│       └── useSimulations.ts
└── types/
    └── api.ts                      # TypeScript types from API
```

---

## Implementation Todos

1. **Setup Next.js Project**
   - Initialize Next.js 14 project with TypeScript, Tailwind CSS, and required dependencies (React Query, Axios, Recharts)

2. **Create API Client**
   - Create typed API client for FastAPI backend with error handling and request/response types

3. **Build Base Components**
   - Build base UI components (Button, Card, Table, Loading states) with mobile-first responsive design

4. **Implement Dashboard**
   - Implement main dashboard showing latest predictions, quick stats, and manual trigger buttons

5. **Create Predictions View**
   - Create predictions list and detail views with algorithm info and historical results

6. **Build Performance Charts**
   - Build performance tracking page with ROI charts, algorithm comparison, and statistics

7. **Create Simulation Interface**
   - Create simulation interface for testing algorithms with date range selection and results display

8. **Add Job Monitoring**
   - Add cron job status monitoring with real-time updates and job history

---

## Next Steps

1. **Decision**: Confirm personal vs business approach
2. **Setup**: Initialize Next.js project with TypeScript
3. **API Client**: Create typed API client for FastAPI backend
4. **Components**: Build base UI components (mobile-first)
5. **Dashboard**: Implement main dashboard with latest predictions
6. **Iterate**: Add features based on usage patterns

---

## Cost Considerations

**Personal Use:**
- Hosting: Vercel (free tier) or Netlify (free tier)
- Domain: ~$10-15/year (optional)
- **Total: ~$0-15/year**

**Business Use:**
- Hosting: Vercel Pro ($20/month) or similar
- Domain: ~$15/year
- Payment processing: Stripe (2.9% + $0.30 per transaction)
- Email service: SendGrid/Mailgun (~$15/month)
- **Total: ~$35-50/month + transaction fees**

---

## Recommendation Summary

- **Start personal** with Next.js + TypeScript + Tailwind
- **Build MVP** in 2-3 days
- **Validate** for 3-6 months
- **Then decide** on business model based on ROI data and legal considerations


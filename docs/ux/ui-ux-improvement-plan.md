# UI/UX Improvement Plan: Partner Portal and Admin Console

- Date: 2026-10-19
- Scope: `frontend/portal` (React 18, customer/partner portal) and `frontend/admin` (Vue 3, operations console)
- Goal: a portal a first-time referrer understands in under a minute, that feels fast and
  alive, and that never leaves them unsure about their money.

## 1. Where the UI is today

Findings from reading the current source, roughly in order of user impact.

### Trust and correctness (fix first)

| # | Finding | Where | Why it matters |
|---|---|---|---|
| T1 | Every API call silently falls back to made-up numbers when the request fails | `portal/src/api.ts` (all `catch` blocks) | A logged-out or offline user sees "৳1,480 available" that isn't real. For a money product this is the single biggest UX risk |
| T2 | Pages start with different fake balances than the API fallback (`1450000` vs `148000`), so numbers visibly jump on load | `Dashboard.tsx`, `Withdrawals.tsx` initial state | Flicker on money values reads as a bug |
| T3 | Hardcoded identity: "Rahim Ahmed", `RAHIM82`, "KYC Verified", "Verified Affiliate" | `App.tsx` header and sidebar | Every user sees someone else's name and a verification status they may not have |
| T4 | Withdrawal amount is parsed as a float (`Number(amount) * 100`); the optimistic balance update uses the unrounded value | `Withdrawals.tsx` | Violates the platform's own no-float rule (ADR 0003) and can show ৳0.01 drift |
| T5 | Withdrawal submits immediately: no review or confirm step for a money movement | `Withdrawals.tsx` | Users can't double-check method and amount before funds go on hold |
| T6 | Payout history is one hardcoded row; "Add Method" and KYC upload do nothing | `Withdrawals.tsx`, `Settings.tsx` | Dead controls erode confidence |
| T7 | Admin "Approve" uses `alert()` and removes the row, even though payouts above the threshold need a second approver | `admin/src/views/PayoutsReview.vue` | Misrepresents maker-checker state to finance staff |

### Clarity

- **Internal jargon in user-facing copy:** "Pending Escrow", "Submit for Maker-Checker
  Review", "Double-entry ledger audited", "Product Tenant", "Payment Reference", "§13".
  Referrers think in "earning", "ready to withdraw" and "on its way".
- **No answer to "when do I get paid?"** Pending commissions show a "Matures At" date
  but no countdown, progress or explanation of the 14-day hold.
- **Status is shown by colour alone** (green/amber badges, green/amber amounts).
- **No first-run experience:** a new referrer with zero referrals sees empty tables.

### Look and feel

- Nearly all styling is inline `style={{…}}` objects. There's no component library, so
  spacing, radius and type sizes drift between pages, and `formatBDT` is copy-pasted
  four times.
- **Product theming doesn't work.** `ThemeContext` picks Healora/PulsePOS colours, but
  nothing applies them to the CSS variables, and the `GET /v1/public/products/{slug}/theme`
  endpoint is never called.
- No motion beyond a few `transition: all 0.15s` hovers; no loading skeletons (just
  "Loading conversions…" text); no dark mode.

### Reach

- Fixed 240 px sidebar with no mobile layout. The spec requires mobile-first (§18), and
  most Bangladeshi referrers will share from a phone.
- The language switch (`en`/`বাংলা`) is a dead `<select>`; no i18n setup exists.
- Accessibility gaps: the header "copy code" control is a clickable `<div>` (not keyboard
  reachable, not announced), and tables overflow on small screens. WCAG 2.1 AA is a spec
  requirement (§18).
- Missing screens from the spec: login and SSO callback, notifications, analytics charts,
  QR and per-product share links (§18).

## 2. Principles

1. **Money is never ambiguous.** Every amount is real or clearly labelled as demo/estimate,
   shows its state in words as well as colour, and says when it changes next.
2. **Plain language first, detail on demand.** Short labels; jargon only in "Learn more"
   popovers.
3. **One primary action per screen.** Dashboard: share. Wallet: withdraw. Admin queue:
   approve or reject.
4. **Motion explains, it doesn't decorate.** Animations show where something came from,
   where it went, or that something succeeded. 150–300 ms, transform/opacity only, and
   fully disabled by `prefers-reduced-motion`.
5. **Phone first.** Every flow works one-handed at 360 px wide.
6. **Accessible by default.** WCAG 2.1 AA, keyboard-complete, screen-reader announcements
   for async results.

## 3. Information architecture and copy

### Portal navigation (5 → 5 items, renamed; bottom tab bar on mobile)

| Today | Proposed | Contents |
|---|---|---|
| Overview | **Home** | Share card, "your money at a glance", next payout date, recent activity |
| Referral Network | **Referrals** | People you referred (masked per product visibility, ADR 0016), status timeline |
| Wallet & Ledger | **Earnings** | Balance breakdown, commission timeline, transaction history |
| Payout Requests | **Withdraw** | Withdraw stepper, saved accounts, payout history |
| Settings & KYC | **Account** | Profile, language, notifications, verification, payout methods |

Notifications move to a bell in the header with an unread count.

### Copy glossary (user-facing → internal)

| Show users | Instead of | Helper text |
|---|---|---|
| Earning (on hold) | Pending / Pending Escrow | "Becomes withdrawable on 22 Oct, after the refund window" |
| Ready to withdraw | Available | |
| Credit | Credit-only | "Can be spent on subscriptions, not withdrawn" |
| On its way | Payout hold / PROCESSING | |
| Paid | PAID | |
| Under review | UNDER_REVIEW / Maker-Checker | "We check large withdrawals for your security, usually within 1 business day" |
| Reversed | REVERSED | "The customer was refunded, so this commission was taken back" |

All strings move into i18n files (`en`, `bn`) from day one, so Bengali is a translation
task rather than a refactor.

## 4. Redesigned key flows

### 4.1 First run (new referrer, zero referrals)

1. Welcome sheet: "You earn 10% of what your friends pay for 12 months." Three steps
   illustrated: share → friend subscribes → you get paid.
2. Personal link, prominent, with **Copy**, **Share** (Web Share API on mobile),
   **WhatsApp**, **Messenger** and **QR** buttons, plus a per-product link picker
   (PulsePOS / Healora).
3. Empty states everywhere use the same illustration plus one action ("Share your link"),
   never an empty table.

### 4.2 Home

- **Money summary card:** one large "Ready to withdraw" number, with a stacked bar showing
  On hold / Ready / Credit / On its way, and a caption such as "৳150 more becomes ready on
  24 Oct".
- **Share card:** link, copy, QR and share sheet.
- **Activity feed** (replaces the conversions table on mobile): "A Healora referral
  subscribed: +৳200 earning".
- **Progress nudge** when tiered rates apply: "2 more conversions this month to reach 12%".

### 4.3 Earnings: commission timeline

Each commission shows a 3-step progress track: **Earned → On hold (refund window) →
Ready**, with the fill animated to today's position and the date it completes. Reversed
commissions show the reason in plain words.

### 4.4 Withdraw: stepper with review

1. **Amount:** big input in taka with quick chips (৳1,000 · ৳5,000 · Max). Inline
   validation as you type against min, max and withdrawable balance. Parsing is
   string → integer minor units with no floats (fixes T4).
2. **Where to:** saved accounts as selectable cards (bKash pink, Nagad orange, bank blue
   icon), plus "Add account" in a sheet with format hints and masking.
3. **Review:** amount, tax withheld, net, destination, expected timing, and why review
   may be needed. **Confirm** is the only primary button.
4. **Done:** animated check, "On its way", timeline of next states, link to history.
   Blocked eligibility (KYC, negative balance, open risk case) explains why and links to
   the fix instead of failing on submit.

### 4.5 Account and verification

- Working KYC upload: drag-and-drop or camera on mobile, preview, progress bar, status
  chip (Not started / In review / Verified / Needs attention) with the reason.
- Language switch takes effect immediately and persists.
- Notification preferences per category; transactional finance notices are always on (§16).

### 4.6 Admin console

- Icons in the nav (lucide is already a dependency), collapsible sidebar, and a
  **⌘K command palette** for "go to payout…", "replay event…", "simulate rule…".
- **Payout review:** side drawer with partner history, risk flags and ledger impact;
  approval state shows "1 of 2 approvals" and who approved; confirm dialog with a typed
  reason for rejections; toasts instead of `alert()` (fixes T7).
- **Events console:** filter chips by state, live counts, JSON viewer with copy, replay
  with confirmation and the resulting state shown inline.
- **Rule simulator:** result card shows the winning rule, the specificity explanation and
  the calculation steps, animated as each step resolves.
- Tables: sticky headers, column density toggle, keyboard row navigation, saved filters.

## 5. Motion system

### Library choice

| App | Library | Why |
|---|---|---|
| Portal (React) | **Motion** (`motion`, formerly Framer Motion) with `LazyMotion` + `domAnimation` | Layout and shared-element animations, `AnimatePresence` for exits; about 20 KB with lazy features |
| Admin (Vue) | Vue built-in `<Transition>` / `<TransitionGroup>` plus CSS | Admin needs restraint and speed; no extra dependency |
| Both | CSS custom properties for durations and easing | One source of truth for timing |

### Tokens

```css
--motion-fast: 120ms;   /* hovers, presses, toggles */
--motion-base: 200ms;   /* most enter/exit, tabs, drawers */
--motion-slow: 320ms;   /* page transitions, success moments */
--ease-out: cubic-bezier(0.16, 1, 0.3, 1);
--ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
```

Springs (Motion only, defined in `portal/src/ui/motion.ts`): `{ type: "spring", stiffness: 380, damping: 30 }`
for sheets and drawers, `{ stiffness: 500, damping: 35 }` for small press feedback.

`@media (prefers-reduced-motion: reduce)` sets every duration to 0 ms and disables
count-ups, confetti and parallax. Motion's `useReducedMotion()` gates the JS animations.

### Animation catalogue

| Moment | Animation | Purpose |
|---|---|---|
| Route change | Content fades in and rises 8 px; sidebar stays put | Orientation without disorientation |
| Data loading | Skeleton blocks with a soft shimmer, shaped like the real content | Perceived speed; no layout jump |
| List and table rows | Stagger in at 30 ms per row (first 8 rows only) | Draws the eye down the list |
| Balance numbers | Count up from 0 on first load only (≤ 600 ms); screen readers get the final value once | Delight without hiding the real number |
| Stacked balance bar | Segments grow left-to-right | Shows the composition of money |
| Copy link | Icon morphs copy → check, and the button says "Copied" for 2 s (`aria-live`) | Clear confirmation |
| Commission timeline | Progress fill eases to today's position | Answers "when do I get paid?" |
| Withdraw stepper | Steps slide horizontally; the review card scales in | Sense of progress |
| Withdrawal success | Check-mark draw plus a small burst | Reward a completed money action |
| First commission ever | One-time confetti, then never again | Celebrate the milestone that matters |
| Toasts | Slide up from bottom (mobile) or top-right (desktop), auto-dismiss with progress | Non-blocking feedback |
| Drawers and sheets | Slide plus backdrop fade; swipe-to-dismiss on mobile | Familiar, native feel |
| Card hover (desktop) | 2 px lift plus shadow | Affordance |
| Admin approve/reject | Row collapses out with `TransitionGroup`; counts animate | Shows the queue shrinking |

Rules: animate only `transform` and `opacity`; never animate a money value after it has
been displayed (no "ticking" on refresh); never delay an action behind an animation.

## 6. Design system foundation

Shared between both apps where possible:

- **Tokens:** move `index.css` / `style.css` variables into one `frontend/shared/tokens.css`
  with light and dark themes (`[data-theme="dark"]` plus `prefers-color-scheme`), the
  motion tokens, and a spacing scale (4 px base).
- **Product theming that works:** fetch `/v1/public/products/{slug}/theme`, write
  `--primary` and related variables on `:root`, and keep contrast at least AA by deriving
  hover/subtle shades and checking text-on-primary contrast at runtime.
- **Portal component kit** (React, in `portal/src/ui/`): `Button`, `IconButton`, `Card`,
  `Stat`, `Money`, `StatusPill`, `Skeleton`, `EmptyState`, `Toast`, `Sheet/Drawer`,
  `Dialog`, `Stepper`, `Tabs`, `Tooltip/Popover`, `CopyField`, `ShareMenu`, `QRCode`,
  `Timeline`, `DataList` (table on desktop, cards on mobile). Built on **Radix UI
  primitives** for accessible behaviour, styled with our tokens.
- **Admin kit** (Vue, `admin/src/ui/`): the same set where relevant, built on Radix Vue
  (Reka UI).
- **Money utilities:** one `formatMoney(minor, currency, locale)` and one
  `parseMoney(text, currency) → minor` (string-based, no floats), mirroring
  `app/core/money.py`, with unit tests.
- **Data layer:** TanStack Query (already in the spec, §2) for caching, retries, loading
  and error states. Remove silent mock fallbacks; demo data lives behind an explicit
  `VITE_DEMO_MODE` flag and shows a visible "Demo data" banner (fixes T1–T2).
- **Typography:** Inter for UI plus a Bengali-capable face (Hind Siliguri or Noto Sans
  Bengali); tabular numerals for all money.

## 7. Accessibility and i18n checklist

- [ ] All interactive elements are real `<button>`/`<a>`; visible focus ring on every one
- [ ] Status always has text, not just colour; contrast ≥ 4.5:1 in both themes
- [ ] Async results announced through one `aria-live` region (copy, save, submit, errors)
- [ ] Dialogs and sheets trap focus and close on Esc; restore focus on close
- [ ] Tables have captions/headers and become labelled card lists under 640 px
- [ ] Touch targets ≥ 44 × 44 px on mobile
- [ ] `react-i18next` / `vue-i18n` with `en` and `bn`; numbers and dates via `Intl`
      (`bn-BD` digits optional per user setting)
- [ ] Axe checks in CI with zero serious violations

## 8. Delivery plan

| Step | Scope | Exit criteria | Size |
|---|---|---|---|
| **U0 Foundations** | Shared tokens (light/dark, motion), money utils with tests, TanStack Query, remove silent mocks + demo banner, real identity in header, theme endpoint applied | No hardcoded user data; a failed API shows an error state, not fake numbers; theme switches per product | M |
| **U1 Component kit** | Portal and admin primitives (section 6), Storybook (Ladle for speed) | Each component has light/dark and reduced-motion stories; axe passes | L |
| **U2 Portal IA and copy** | New nav, mobile bottom tabs, responsive shell, i18n wiring, glossary copy | Every screen usable at 360 px; all strings in `en.json` | M |
| **U3 Portal flows** | First run, Home, commission timeline, withdraw stepper with review, payout method sheet, KYC upload, notifications | Playwright E2E: share → withdraw happy path and the blocked-eligibility path | L |
| **U4 Motion pass** | Section 5 catalogue on top of U1–U3 | 60 fps on a mid-range Android (Chrome DevTools 4× CPU throttle); reduced-motion snapshot has no animation | M |
| **U5 Admin console** | Nav and icons, ⌘K, payout drawer with real maker-checker state, toasts and confirm dialogs, events console filters, simulator explanation | E2E: approve requires a second admin above the threshold; replay shows the result state | M |
| **U6 Polish and verify** | Bengali translation review, dark-mode pass, Lighthouse, usability test with 5 referrers (3 on phones) | Lighthouse ≥ 90 performance and 100 accessibility on Home; 4 of 5 users find "when do I get paid" in under 30 s | S |

Order matters: U0 fixes the trust issues before anything gets prettier, and U4 comes after
the components exist so animations are added once, in the kit, not per page.

## 9. Measures of success

- Time for a new user to copy or share their link: < 15 s from first load
- Withdrawal flow completion rate (started → confirmed) ≥ 85%; support tickets about
  "where is my money" down after the timeline ships
- Zero places where a failed request shows a non-real balance
- Axe: 0 serious/critical issues; Lighthouse accessibility 100
- Core Web Vitals on a 4G phone: LCP < 2.5 s, INP < 200 ms, CLS < 0.05 (skeletons sized to
  content prevent layout shift)
- JS budget: portal initial bundle < 180 KB gzipped including the motion library

## 10. Decisions needed

| Question | Recommendation |
|---|---|
| Keep two frontend stacks (React portal, Vue admin)? (ADR 0020) | Keep for now; the plan works for both, but a single React stack would let the admin reuse the portal kit and cut U1 and U5 effort by about a third |
| Animation library for the portal | Motion with `LazyMotion` |
| Dark mode in the first release? | Yes; tokens make it cheap if done in U0 |
| Bengali at launch or later? | Wire i18n in U2 regardless; translation can ship a step later |
| Brand identity: does the platform have its own logo, colours and type, or should it stay neutral and take on each product's theme? | Neutral platform shell plus per-product theming |

## 11. Implementation status (2026-10-20)

Defaults used for section 10: both stacks kept, dark mode shipped, English + Bengali wired,
neutral shell with per-product theming.

| Step | Status | Notes |
|---|---|---|
| U0 Foundations | Done | `frontend/shared/tokens.css` (light/dark, motion, reduced motion); exact money parse/format (`portal/src/lib/money.ts`, 27 tests); TanStack Query; no silent mock fallbacks; explicit demo mode with a persistent banner in both apps; real identity from `/v1/me`; product theme from `/v1/public/products/{slug}/theme` with automatic AA contrast correction |
| U1 Component kit | Done, without Storybook | Portal `src/ui/*` (Radix dialog/popover), admin `src/components/*` (own focus-trapped dialog/drawer). Storybook/Ladle not set up |
| U2 Portal IA + copy | Done | Home / Referrals / Earnings / Withdraw / Account, bottom tab bar under 860 px, plain-language copy in `src/i18n/en.ts` + `bn.ts` |
| U3 Portal flows | Done | First-run welcome, share card (copy, native share, WhatsApp, Messenger, QR), commission timeline, 3-step withdraw with review and live validation, add-account sheet, KYC upload (drag/drop + camera), notifications sheet, sign-in + SSO callback |
| U4 Motion | Done | Section 5 catalogue; motion features lazy-loaded; `MotionConfig reducedMotion="user"` + CSS token zeroing |
| U5 Admin console | Done | Icon nav in sections, collapsible sidebar, ⌘K palette, theme + density toggles, payout drawer + confirm dialogs (reason required for reject / mark-paid / approvals above threshold), toasts instead of `alert()`, events filters + search + replay confirm, simulator with specificity explanation, real audit log. Support desk view kept; colours moved to tokens |
| U6 Polish + verify | Partly done | Done: axe (WCAG 2.1 AA + best practice) on every portal and admin page in light and dark: 0 violations; 37 portal tests incl. page-level axe; bundle 147 KB gz initial (budget 180). Not done: native-speaker review of `bn.ts`, Lighthouse run, usability test with 5 referrers |

### Backend gaps found while wiring real data

| Gap | Effect in the UI |
|---|---|
| No `GET /v1/me/referrals` | Referrals page shows "not available yet" (spec'd in `docs/openapi.yaml`) |
| No `GET /v1/me/payouts` | Withdrawal history shows "not available yet" |
| No KYC upload endpoint (UI posts to `/v1/me/kyc`) | Upload shows "contact support" when the endpoint is missing |
| Payout approve moves straight to `APPROVED` with one approver | Drawer warns that policy needs two approvers above the threshold; a note is required |
| Events endpoint has no payload or error message | Drawer shows the record only |
| Programme terms (rate, months, hold days, limits) not exposed | Read from `VITE_*` env with spec defaults (`portal/src/app/program.ts`) |

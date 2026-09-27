# Business lens — lotto-predictore

**North star:** Every change should help **prove this app improves your chances enough to justify spending money on it**, or **earn extra income from using it** — with proof first, monetization second.

## Primary goal (validation)

**Prove the app actually improves lottery chances in a way worth investing money.**

“Worth investing” means a **skeptical person with a wallet** would say: the cost of tickets + tooling + time is rational because measured results beat honest baselines — not because the UI feels lucky.

| Signal | Where it lives | Why it matters |
| ------ | -------------- | -------------- |
| Out-of-sample performance | Walk-forward scoreboard, `/walk-forward/summaries` | In-sample backtests lie; walk-forward is the honesty check |
| Real play vs model | `RealTicketBatch` settlement after each draw | Predictions never submitted and scored do not count as proof |
| ROI vs cost of play | Official Pais prize tiers (`pais_csv`, `draw_prize`) | ROI without real prize rows is invalid — keep ingest integrity |
| Baseline comparison | Random / naive play on the same draws | “Better chances” must be **quantified**, not assumed |

**Non-negotiables**

- Never promise guaranteed profit. Lotto is negative expected value; the claim is **relative improvement in chances / ROI vs baseline**, not certainty.
- Stored draws disagree with the official CSV → **stop new ticket packs** until fixed (`integrity_blocked`).
- Anything that pretties numbers but weakens measurement (silent fallbacks, fake prizes, daily Magayo as source of truth) **blocks the primary goal**.

**Primary is on track when**

- Walk-forward plus settled real batches show **sustained** edge over a documented baseline across **many draws**, not one hot week.
- Methodology is reproducible: official results, logged `source`, scoreboard anyone paying can audit.

## Secondary goal (revenue)

**הכנסה נוספת משימוש בזה** — additional income from **using** this product (your play, paid access, packs, alerts, or other monetization tied to the same track record).

Revenue is **secondary until primary proof is honest**. Selling before measurement is trustworthy = churn and reputational damage.

When proof is credible, prefer revenue that **reuses the same public stats** (scoreboard access, packs aligned with published walk-forward, notifications users already trust). Do not outrun validation with billing complexity or growth hacks.

## How to decide

1. **Primary first** — official ingest, walk-forward, settlement, prize backfill, integrity gates, auditable ROI.
2. **Secondary second** — monetization only when stats are trustworthy; price disclosed performance, not vibes.
3. **Neither** — record the idea; do not ship code that burns latency and trust for “nice to have.”

## Out of scope

- Refactors and elegance with no effect on proof or revenue.
- Features that increase ticket volume without improving **measured** chances (engagement without validation).

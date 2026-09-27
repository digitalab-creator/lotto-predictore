# Business lens — lotto-predictore

## The question

**האם תוצאות עתידיות בפועל מתנהגות באופן שאינו אקראי, והאם האלגוריתם מצליח לנצל את זה מחוץ לנתונים שעליהם הוא נבנה?**

Two parts. Both must be yes, on **future real draws**, before anyone spends more money or sells the product.

1. **Are future actual results non-random?**  
   Look only at draws that have not happened yet when the test is designed. If those draws look like a fair lottery, there is nothing to exploit. Stop that idea.

2. **Does the algorithm use that, outside the data it was built on?**  
   Fitting history is not enough. The method must be frozen, then scored on later draws it never saw (walk-forward). A model that only looks good on the rows used to build it has not answered the question.

**Starting fact:** A past analysis of this data **did not** show that. Do not treat the current logic as a yes.

## Primary goal

**Change the logic and run enough honest tests until that question is answered yes** — or until a test shows the idea is random and should be dropped.

| What to do | Why |
| ---------- | --- |
| Try a new rule, feature, or model | The old analysis did not find a usable pattern |
| Freeze it before the next draws | Part 2 fails if you peek at the answers first |
| Score future official draws only | Part 1 is about results that actually happened later (`pais_csv`, `draw_prize`) |
| Compare to random / naive play | “Not random” and “we exploited it” need a baseline, not a feeling |
| Keep ingest honest | Wrong numbers make both answers fake (`integrity_blocked` stops new packs) |

**Non-negotiables**

- Never claim a yes from in-sample fit, one lucky week, or unlabeled fallbacks.
- Never promise guaranteed profit. The bar is: future draws are not pure noise, **and** this algorithm captures that out of sample.
- Pretty charts and more tickets from a method that failed part 2 are not progress.

**Primary is done only when** both parts stay yes over many future draws, long enough that buying more tickets is a rational bet.

## Secondary goal

**הכנסה נוספת משימוש בזה** — extra income from using the product.

Only after the question above is yes. Selling before that is selling a pattern the last analysis did not find.

## Resource goal (always on)

This app is heavy. **Use as much CPU and memory as this server can spare, and cause zero interruption to every other app on the same machine.**

| Rule | Meaning |
| ---- | ------- |
| Take leftovers | When the host is idle, lotto may grow (training, scoring, experiments). Spare capacity should not sit unused. |
| Yield immediately | When another container or app needs CPU or RAM, lotto shrinks. Neighbors always win a fight. |
| One mechanism | `config/resource_governor.yaml` and `scripts/resource_governor.py`. Do not add a second limiter. |

Zero interruption means other apps stay responsive: no CPU steal, no memory pressure that slows or kills them, no disk fill from lotto logs or models. A faster experiment that makes WordPress, n8n, or anything else stutter is a failed change.

## How to decide

1. **Primary** — the next experiment that can answer the question (or kill a false yes).
2. **Resource** — let that experiment use spare CPU/RAM, and back off the moment another app needs the box.
3. **Secondary** — revenue only after both parts of the question are yes out of sample.
4. **Neither** — record it; do not build it.

## Out of scope

- Refactors that do not help the next out-of-sample test.
- More ticket volume from a method that has not beaten chance on future draws.
- Raising lotto limits in a way that can stall other apps, even if the model would finish sooner.

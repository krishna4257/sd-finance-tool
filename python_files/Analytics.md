### WHEN WILL THE VILLAGE HEALTH CACHE BE FILLED/RELOADED? ###

The village_health_cache is designed with a hybrid invalidation and pre-computation model to guarantee both real-time accuracy and instant page loads. Here are the scenarios where the cache is filled, recalculated, or reloaded:

1. Event-Driven Real-time Invalidation (Lazy Reloading)
Whenever any data that affects a customer's payment health or loan schedule changes, the cache is invalidated for that specific village. This ensures the app never shows stale data. The next time someone visits the dashboard or opens a history chart for that village, the backend detects the cache miss, computes the new ratings, and updates the cache.

The specific invalidation triggers are:

Payment Operations:
Posting/Creating a new payment.
Updating a payment's amount or date.
Deleting a payment.
Bulk updates to payment dates (e.g., shifting/correcting posting lags).
Customer Profile Operations:
Registering/Creating a new customer.
Editing customer parameters (e.g., changing loan amount, installment, or start/end dates).
Activating, deactivating, or closing a customer account.
Deleting a customer profile.

2. Scheduled Daily Recalculation & Cache Warming (Active Pre-population)
A background scheduler task (execute_daily_rating_recalculation) runs automatically at 5:00 AM IST daily. This task performs two steps:

Recalculates Ratings: Loops through all active customers with outstanding balances (balance_amount > 0) to recalculate their repayment rating details.
Warms Up Cache: Identifies all active villages (villages with active loans) and systematically pre-calculates the health statistics and history charts for all ranges (weekly, monthly, yearly, complete) and views (active_only, active_defaulted, complete). It saves these directly to the village_health_cache table.
This ensures that at the start of every business day, the dashboard for all active villages loads instantly.

3. Manual Force-Recalculation (User-Driven)
The frontend dashboard features a "Refresh" button. When clicked, it passes force_recalc=true to the backend.

This deletes all cached items for that specific village in village_health_cache.
It forces a live, synchronous recalculation of the behavioral analytics and health score, overwriting the cache.
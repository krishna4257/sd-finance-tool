/**
 * SD Finance PWA - Transaction Synchronization Engine
 * Automatically queues and flushes offline payments to /api/mobile/payment_feed_batch.
 */
class SyncManager {
  constructor() {
    this.isSyncing = false;
    this.listeners = [];

    // Auto-sync listeners
    window.addEventListener('online', () => {
      this._notifyStatus('online');
      this.syncAll();
    });

    window.addEventListener('offline', () => {
      this._notifyStatus('offline');
    });
  }

  onStatusChange(fn) {
    this.listeners.push(fn);
  }

  _notifyStatus(status, details = {}) {
    for (const fn of this.listeners) {
      fn(status, details);
    }
  }

  isOnline() {
    return navigator.onLine;
  }

  async syncAll() {
    if (this.isSyncing) return { status: 'already_running' };
    if (!this.isOnline()) {
      this._notifyStatus('offline');
      return { status: 'offline' };
    }

    const token = await window.dbService.getSession('token');
    if (!token) return { status: 'not_authenticated' };

    this.isSyncing = true;
    this._notifyStatus('syncing');

    let totalSynced = 0;
    let errors = [];

    try {
      // 1. Sync Pending Payments
      const pendingPayments = await window.dbService.getPendingPayments();

      if (pendingPayments.length > 0) {
        const eid = await window.dbService.getSession('eid');
        const deviceId = await window.apiClient.getDeviceId();

        // Group payments by village ID
        const byVillage = {};
        for (const p of pendingPayments) {
          const v = p.vid || 0;
          if (!byVillage[v]) byVillage[v] = [];
          byVillage[v].push(p);
        }

        for (const vid of Object.keys(byVillage)) {
          const batch = byVillage[vid];
          const payload = {
            vid: parseInt(vid, 10),
            eid: parseInt(eid, 10),
            device_id: deviceId,
            payments: batch.map(p => {
              const amt = parseFloat(p.amt || p.amount || 0);
              const pType = (p.payment_type || 'cash').toLowerCase();
              return {
                local_uuid: p.local_uuid || p.uuid,
                ano: parseInt(p.ano, 10),
                vid: parseInt(p.vid || vid, 10),
                eid: parseInt(p.eid || eid, 10),
                amt: amt,
                cash_amount: p.cash_amount !== undefined ? parseFloat(p.cash_amount) : (pType === 'cash' ? amt : 0),
                upi_amount: p.upi_amount !== undefined ? parseFloat(p.upi_amount) : (pType === 'upi' ? amt : 0),
                payment_date: p.payment_date,
                payment_type: pType,
                latitude: p.latitude || null,
                longitude: p.longitude || null,
                accuracy: p.accuracy || null,
                gps_status: p.gps_status || 'unavailable'
              };
            })
          };

          try {
            await window.apiClient.postPaymentBatch(payload);

            // Mark each payment in this batch as synced
            for (const p of batch) {
              await window.dbService.updatePaymentStatus(p.local_uuid, 'synced');
              totalSynced++;
            }
          } catch (batchErr) {
            console.error(`Failed to sync payment batch for village ${vid}:`, batchErr);
            errors.push(`Village ${vid}: ${batchErr.message}`);
            for (const p of batch) {
              await window.dbService.updatePaymentStatus(p.local_uuid, 'failed', batchErr.message);
            }
          }
        }
      }

      // 2. Sync Pending Customers (if any)
      const pendingCustomers = await window.dbService.getPendingCustomers();
      if (pendingCustomers.length > 0) {
        for (const c of pendingCustomers) {
          try {
            const custPayload = c.payload || c;
            await window.apiClient.postCustomer(custPayload);
            await window.dbService.updateCustomerStatus(c.local_uuid, 'synced');
            totalSynced++;
          } catch (custErr) {
            console.error(`Failed to sync customer ${c.local_uuid}:`, custErr);
            errors.push(`Customer ${c.ano || ''}: ${custErr.message}`);
            await window.dbService.updateCustomerStatus(c.local_uuid, 'failed', custErr.message);
          }
        }
      }

      // 3. Sync Pending Close Account requests
      const pendingCloses = await window.dbService.getPendingCloseAccounts();
      if (pendingCloses.length > 0) {
        for (const item of pendingCloses) {
          try {
            await window.apiClient.closeAccountFeed(item.payload || item);
            await window.dbService.updateCloseAccountStatus(item.local_uuid, 'synced');
            totalSynced++;
          } catch (closeErr) {
            console.error(`Failed to sync close account ${item.local_uuid}:`, closeErr);
            errors.push(`Close A/C ${item.ano || ''}: ${closeErr.message}`);
            await window.dbService.updateCloseAccountStatus(item.local_uuid, 'failed', closeErr.message);
          }
        }
      }

      const pendingRemaining = await window.dbService.getPendingCount();
      const result = {
        status: errors.length > 0 ? 'partial' : 'success',
        synced: totalSynced,
        pendingRemaining,
        errors
      };

      this._notifyStatus('completed', result);
      return result;
    } catch (err) {
      console.error('Fatal error during syncAll:', err);
      this._notifyStatus('error', { error: err.message });
      return { status: 'error', error: err.message };
    } finally {
      this.isSyncing = false;
    }
  }
}

window.syncManager = new SyncManager();

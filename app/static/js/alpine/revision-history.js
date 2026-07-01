/**
 * revisionHistory — Alpine.data component for entry revision timeline (§6).
 *
 * Fetches paginated revisions from /api/entries/{entryId}/revisions,
 * renders a collapsible change summary, and loads full detail on click.
 *
 * Usage:
 *   <div x-data="revisionHistory(entryId)" class="card mt-4">
 *     <div class="card-header" @click="toggle = !toggle">Revision History</div>
 *     <div x-show="toggle">...</div>
 *   </div>
 */

(function () {
  'use strict';

  document.addEventListener('alpine:init', function () {
    Alpine.data('revisionHistory', function (entryId) {
      return {
        entryId: entryId,
        toggle: false,
        loading: false,
        revisions: [],
        total: 0,
        page: 1,
        perPage: 10,
        expandedRev: null,   // revision_number of the detail panel
        detailData: null,     // {snapshot, change_report} for expandedRev
        detailLoading: false,
        error: null,

        init: function () {
          // Auto-load on toggle; no need to load at init
        },

        /** Fetch the paginated revision list. */
        loadRevisions: function () {
          if (this.loading) return;
          this.loading = true;
          this.error = null;
          var self = this;
          var url = '/api/entries/' + encodeURIComponent(this.entryId)
                  + '/revisions?page=' + this.page + '&per_page=' + this.perPage;
          // Debug: log the URL being called
          if (window.console) console.log('[revisionHistory] Loading from:', url, 'entryId:', this.entryId);
          fetch(url)
            .then(function (r) { return r.json(); })
            .then(function (data) {
              self.revisions = data.revisions || [];
              self.total = data.total || 0;
              if (window.console) console.log('[revisionHistory] Loaded:', self.total, 'revisions', data);
              self.loading = false;
            })
            .catch(function (err) {
              self.error = 'Failed to load revisions: ' + err.message;
              if (window.console) console.error('[revisionHistory] Error:', err);
              self.loading = false;
            });
        },

        /** Load more (next page). */
        loadMore: function () {
          if (this.loading || this.revisions.length >= this.total) return;
          this.page++;
          var self = this;
          var url = '/api/entries/' + encodeURIComponent(this.entryId)
                  + '/revisions?page=' + this.page + '&per_page=' + this.perPage;
          fetch(url)
            .then(function (r) { return r.json(); })
            .then(function (data) {
              self.revisions = self.revisions.concat(data.revisions || []);
              self.loading = false;
            })
            .catch(function () {
              self.page--; // revert
              self.loading = false;
            });
        },

        /** Toggle the panel visibility and load revisions if needed. */
        togglePanel: function () {
          this.toggle = !this.toggle;
          if (this.toggle && this.revisions.length === 0) {
            this.loadRevisions();
          }
        },

        /** Toggle detail for a revision. Fetches full snapshot on first open. */
        toggleDetail: function (revNumber) {
          if (this.expandedRev === revNumber) {
            this.expandedRev = null;
            this.detailData = null;
            return;
          }
          this.expandedRev = revNumber;
          this.detailData = null;
          this.detailLoading = true;
          var self = this;
          var url = '/api/entries/' + encodeURIComponent(this.entryId)
                  + '/revisions/' + revNumber;
          fetch(url)
            .then(function (r) { return r.json(); })
            .then(function (data) {
              self.detailData = data.revision || null;
              self.detailLoading = false;
            })
            .catch(function () {
              self.detailLoading = false;
            });
        },

        /** Human-friendly date display. */
        formatDate: function (iso) {
          if (!iso) return '';
          var d = new Date(iso);
          return d.toLocaleString(undefined, {
            year: 'numeric', month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
          });
        },

        /** CSS class for a change kind. */
        changeClass: function (kind) {
          if (kind === 'added') return 'text-success';
          if (kind === 'removed') return 'text-danger';
          if (kind === 'modified') return 'text-warning';
          return '';
        }
      };
    });
  });
})();

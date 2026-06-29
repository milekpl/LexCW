/**
 * rangeElements — Alpine.data component for the range elements tree (§ranges-editor).
 *
 * Flattens the nested element tree on load, then renders via x-for.
 * A separate visibleNodes array is computed whenever the expanded set changes,
 * so only visible nodes produce DOM elements — O(n) per toggle, not O(n²).
 *
 * Registered as Alpine.data('rangeElements', ...) on alpine:init.
 */
(function () {
  'use strict';

  document.addEventListener('alpine:init', function () {
    Alpine.data('rangeElements', function () {
      return {
        rangeId: null,
        flatNodes: [],
        visibleNodes: [],
        expandedSet: new Set(),
        totalElements: 0,
        depth: 0,
        loading: false,

        /**
         * Flatten a nested element tree into a flat array with depth info.
         */
        _flatten(elements, depth) {
          var out = [];
          if (!elements) return out;
          for (var i = 0; i < elements.length; i++) {
            var elem = elements[i];
            var hasChildren = !!(elem.children && elem.children.length > 0);
            var childCount = hasChildren ? elem.children.length : 0;
            var abbrev = elem.effective_abbrev || elem.abbrev || '';
            if (!abbrev && elem.abbrevs) {
              abbrev = elem.abbrevs['en'] || '';
              if (!abbrev) {
                var vals = Object.values(elem.abbrevs);
                abbrev = vals.length > 0 ? vals[0] : '';
              }
            }
            var label = elem.effective_label || '';
            if (!label && elem.labels) {
              label = elem.labels['en'] || '';
              if (!label) {
                var lvals = Object.values(elem.labels);
                label = lvals.length > 0 ? lvals[0] : '';
              }
            }
            if (!label) label = elem.value || elem.id;

            var desc = '';
            if (elem.description) {
              desc = elem.description['en'] || '';
              if (!desc) {
                var dvals = Object.values(elem.description);
                desc = dvals.length > 0 ? dvals[0] : '';
              }
            }

            var multiAbbrevs = [];
            if (elem.abbrevs && Object.keys(elem.abbrevs).length > 0) {
              multiAbbrevs = Object.entries(elem.abbrevs).map(function (entry) {
                return { lang: entry[0], abbr: entry[1] };
              });
            }

            out.push({
              _flatIndex: out.length,
              id: elem.id,
              rangeId: this.rangeId,
              depth: depth,
              abbrev: abbrev,
              label: label,
              desc: desc,
              multiAbbrevs: multiAbbrevs,
              hasChildren: hasChildren,
              childCount: childCount,
              guid: elem.guid || '',
              parent: elem.parent || '',
              value: elem.value || '',
              language: elem.language || ''
            });

            if (hasChildren) {
              var childNodes = this._flatten(elem.children, depth + 1);
              for (var j = 0; j < childNodes.length; j++) {
                out.push(childNodes[j]);
              }
            }
          }
          return out;
        },

        /**
         * Recompute the visibleNodes array from flatNodes + expandedSet.
         * A node is visible if every ancestor on the stack is expanded.
         * O(n) — single pass.
         */
        _recomputeVisible() {
          var visible = [];
          // Stack of depths of expanded ancestors currently open.
          // Only nodes whose parent chain is all-expanded are pushed here,
          // so a node is visible iff openDepths top === node.depth - 1 (or depth === 0).
          var openDepths = [];

          for (var i = 0; i < this.flatNodes.length; i++) {
            var node = this.flatNodes[i];

            // Pop siblings and deeper nodes off the stack
            while (openDepths.length > 0 && openDepths[openDepths.length - 1] >= node.depth) {
              openDepths.pop();
            }

            // Root nodes are always visible.
            // Non-root nodes are visible only if the stack top is their parent's depth.
            var isVisible = (node.depth === 0) ||
              (openDepths.length > 0 && openDepths[openDepths.length - 1] === node.depth - 1);

            if (isVisible) {
              visible.push(node);
            }

            // If this node is visible, has children, and is expanded,
            // push its depth so its children (depth+1) can be visible.
            if (isVisible && node.hasChildren && this.expandedSet.has(node.id)) {
              openDepths.push(node.depth);
            }
          }

          this.visibleNodes = visible;
        },

        /**
         * Load elements for a range from the API and populate the flat list.
         */
        async loadElements(rangeId) {
          this.rangeId = rangeId;
          this.loading = true;
          this.flatNodes = [];
          this.visibleNodes = [];
          this.expandedSet = new Set();

          try {
            var response = await fetch('/api/ranges-editor/' + encodeURIComponent(rangeId) + '/elements');
            var result = await response.json();

            if (!result.success) {
              this.loading = false;
              return;
            }

            var elements = result.data || [];
            this.flatNodes = this._flatten(elements, 0);
            this.totalElements = this.flatNodes.length;

            // Compute max depth
            var maxDepth = 0;
            for (var i = 0; i < this.flatNodes.length; i++) {
              if (this.flatNodes[i].depth > maxDepth) maxDepth = this.flatNodes[i].depth;
            }
            this.depth = maxDepth;

            // Auto-expand top level only (depth 0) so the user sees first-level children
            // without being overwhelmed.
            for (var i = 0; i < this.flatNodes.length; i++) {
              if (this.flatNodes[i].hasChildren && this.flatNodes[i].depth === 0) {
                this.expandedSet.add(this.flatNodes[i].id);
              }
            }

            this._recomputeVisible();
            this.loading = false;
          } catch (e) {
            console.error('[rangeElements] loadElements failed:', e);
            this.loading = false;
          }
        },

        /**
         * Toggle expanded state for a node and recompute visible nodes.
         */
        toggleExpand(nodeId) {
          if (this.expandedSet.has(nodeId)) {
            this.expandedSet.delete(nodeId);
            // Also collapse all descendants (nodes between this and next sibling)
            var nodeIdx = -1;
            var nodeDepth = 0;
            for (var i = 0; i < this.flatNodes.length; i++) {
              if (this.flatNodes[i].id === nodeId) {
                nodeIdx = i;
                nodeDepth = this.flatNodes[i].depth;
                break;
              }
            }
            if (nodeIdx >= 0) {
              for (var j = nodeIdx + 1; j < this.flatNodes.length; j++) {
                if (this.flatNodes[j].depth <= nodeDepth) break;
                this.expandedSet.delete(this.flatNodes[j].id);
              }
            }
          } else {
            this.expandedSet.add(nodeId);
          }
          this._recomputeVisible();
        },

        /**
         * Check if a node is expanded.
         */
        isExpanded(nodeId) {
          return this.expandedSet.has(nodeId);
        },

        /**
         * Expand all nodes.
         */
        expandAll() {
          for (var i = 0; i < this.flatNodes.length; i++) {
            if (this.flatNodes[i].hasChildren) {
              this.expandedSet.add(this.flatNodes[i].id);
            }
          }
          this._recomputeVisible();
        },

        /**
         * Collapse all nodes.
         */
        collapseAll() {
          this.expandedSet = new Set();
          this._recomputeVisible();
        },

        /**
         * Edit element via the parent RangesEditor instance.
         */
        editElement(rangeId, elementId) {
          if (typeof window.editor !== 'undefined' && window.editor.editElement) {
            window.editor.editElement(rangeId, elementId);
          }
        },

        /**
         * Delete element via the parent RangesEditor instance.
         */
        deleteElement(rangeId, elementId) {
          if (typeof window.editor !== 'undefined' && window.editor.deleteElement) {
            window.editor.deleteElement(rangeId, elementId);
          }
        }
      };
    });
  });
})();

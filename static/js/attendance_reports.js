/**
 * Attendance reports panel — in-place filter/preset/pagination (no full page reload).
 */
(function () {
  'use strict';

  function showReportsTab() {
    const tab = document.getElementById('reports-tab');
    if (tab && window.bootstrap && bootstrap.Tab) {
      bootstrap.Tab.getOrCreateInstance(tab).show();
    }
  }

  function openFiltersIfNeeded(panel) {
    const urlParams = new URLSearchParams(window.location.search);
    const hasFilters =
      urlParams.has('student_ids') ||
      urlParams.has('class_ids') ||
      urlParams.get('status') ||
      urlParams.has('page');
    if (!hasFilters) return;
    const filtersEl = panel.querySelector('#attnReportsFilters');
    if (filtersEl && window.bootstrap && bootstrap.Collapse) {
      bootstrap.Collapse.getOrCreateInstance(filtersEl, { toggle: false }).show();
    }
  }

  async function loadReportsPanel(url) {
    const panel = document.getElementById('attendance-reports-panel');
    if (!panel) {
      window.location.href = url;
      return;
    }

    panel.classList.add('attn-reports--loading');
    try {
      const response = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin',
      });
      if (!response.ok) {
        throw new Error('Failed to load reports');
      }
      const html = await response.text();
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const next = doc.getElementById('attendance-reports-panel');
      if (!next) {
        window.location.href = url;
        return;
      }
      panel.replaceWith(next);
      window.history.replaceState(null, '', url);
      showReportsTab();
      bindReportsPanel(next);
      openFiltersIfNeeded(next);
    } catch (err) {
      console.error(err);
      window.location.href = url;
    } finally {
      document.getElementById('attendance-reports-panel')?.classList.remove('attn-reports--loading');
    }
  }

  function buildReportsUrl(form) {
    const params = new URLSearchParams(new FormData(form));
    if (form.dataset.embedTab === '1') {
      params.set('reports_tab', '1');
    }
    params.delete('page');
    const qs = params.toString();
    return qs ? `${form.action}?${qs}` : form.action;
  }

  function bindReportsPanel(panel) {
    const form = panel.querySelector('.attn-reports-filters-form');
    if (form) {
      form.addEventListener('submit', function (event) {
        event.preventDefault();
        loadReportsPanel(buildReportsUrl(form));
      });
    }

    panel.querySelectorAll('a.attn-reports-preset').forEach(function (link) {
      link.addEventListener('click', function (event) {
        event.preventDefault();
        loadReportsPanel(link.href);
      });
    });

    panel.querySelectorAll('.attn-reports-pagination a.page-link[href]').forEach(function (link) {
      link.addEventListener('click', function (event) {
        event.preventDefault();
        loadReportsPanel(link.href);
      });
    });

    const reset = panel.querySelector('.attn-reports-reset');
    if (reset) {
      reset.addEventListener('click', function (event) {
        event.preventDefault();
        loadReportsPanel(reset.href);
      });
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    const panel = document.getElementById('attendance-reports-panel');
    if (panel) {
      bindReportsPanel(panel);
    }
  });
})();

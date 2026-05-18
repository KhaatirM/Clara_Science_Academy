/**
 * Attendance analytics — in-place date/filter updates and client-side search/export.
 */
(function () {
  'use strict';

  async function loadAnalyticsPanel(url) {
    const panel = document.getElementById('attendance-analytics-panel');
    if (!panel) {
      window.location.href = url;
      return;
    }

    panel.classList.add('attn-analytics--loading');
    try {
      const response = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin',
      });
      if (!response.ok) throw new Error('Failed to load analytics');
      const html = await response.text();
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const next = doc.getElementById('attendance-analytics-panel');
      if (!next) {
        window.location.href = url;
        return;
      }
      panel.replaceWith(next);
      window.history.replaceState(null, '', url);
      bindAnalyticsPanel(next);
    } catch (err) {
      console.error(err);
      window.location.href = url;
    } finally {
      document.getElementById('attendance-analytics-panel')?.classList.remove('attn-analytics--loading');
    }
  }

  function buildAnalyticsUrl(form) {
    const params = new URLSearchParams(new FormData(form));
    const qs = params.toString();
    return qs ? `${form.action}?${qs}` : form.action;
  }

  function bindStudentSearch(panel) {
    const input = panel.querySelector('.attn-analytics-search');
    const table = panel.querySelector('#attnAnalyticsTable');
    if (!input || !table) return;

    input.addEventListener('input', function () {
      const q = input.value.trim().toLowerCase();
      table.querySelectorAll('tbody tr').forEach(function (row) {
        const name = (row.getAttribute('data-student-name') || '').toLowerCase();
        row.classList.toggle('attn-analytics-row-hidden', q.length > 0 && !name.includes(q));
      });
    });
  }

  function exportAnalyticsCsv() {
    const table = document.getElementById('attnAnalyticsTable');
    if (!table) {
      alert('No student data to export for the current filters.');
      return;
    }

    const start = table.getAttribute('data-export-start') || '';
    const end = table.getAttribute('data-export-end') || '';
    let csv = 'Student,Grade,Attendance Rate,Present,Absent,Late,Max Consecutive Absences,Risk Level\n';

    table.querySelectorAll('tbody tr:not(.attn-analytics-row-hidden)').forEach(function (row) {
      const cells = row.querySelectorAll('td');
      if (cells.length < 8) return;
      const rowData = [
        cells[0].textContent.trim(),
        cells[1].textContent.trim(),
        cells[2].textContent.trim(),
        cells[3].textContent.trim(),
        cells[4].textContent.trim(),
        cells[5].textContent.trim(),
        cells[6].textContent.trim(),
        cells[7].textContent.trim(),
      ];
      csv += rowData.map(function (v) {
        return '"' + v.replace(/"/g, '""') + '"';
      }).join(',') + '\n';
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'attendance_analytics_' + start + '_to_' + end + '.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  function bindAnalyticsPanel(panel) {
    const form = panel.querySelector('.attn-analytics-filters-form');
    if (form) {
      form.addEventListener('submit', function (event) {
        event.preventDefault();
        loadAnalyticsPanel(buildAnalyticsUrl(form));
      });
    }

    panel.querySelectorAll('a.attn-analytics-preset').forEach(function (link) {
      link.addEventListener('click', function (event) {
        event.preventDefault();
        loadAnalyticsPanel(link.href);
      });
    });

    const reset = panel.querySelector('.attn-analytics-reset');
    if (reset) {
      reset.addEventListener('click', function (event) {
        event.preventDefault();
        loadAnalyticsPanel(reset.href);
      });
    }

    bindStudentSearch(panel);
  }

  document.addEventListener('DOMContentLoaded', function () {
    const panel = document.getElementById('attendance-analytics-panel');
    if (panel) bindAnalyticsPanel(panel);

    const exportBtn = document.getElementById('attnAnalyticsExportBtn');
    if (exportBtn) {
      exportBtn.addEventListener('click', exportAnalyticsCsv);
    }
  });
})();

/**
 * Non-blocking feedback (toasts) for staff dashboards.
 * Use showAppToast() instead of alert() for success/error messages.
 * Corner toasts auto-dismiss after a few seconds (unlike academic concerns).
 */
(function () {
    'use strict';

    function escapeHtml(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    function showAppToast(message, type) {
        if (!message) return;
        var toastType = type || 'info';
        if (toastType === 'error') toastType = 'danger';

        var toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            /* Bottom-right corner toasts (same region as academic concerns; auto-dismiss). */
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            toastContainer.style.zIndex = '1090';
            document.body.appendChild(toastContainer);
        }

        var toast = document.createElement('div');
        toast.className = 'toast align-items-center text-bg-' + toastType + ' border-0 shadow';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');
        toast.setAttribute('aria-atomic', 'true');
        toast.innerHTML =
            '<div class="d-flex">' +
            '<div class="toast-body">' + escapeHtml(message) + '</div>' +
            '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>' +
            '</div>';

        toastContainer.appendChild(toast);
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            var bsToast = new bootstrap.Toast(toast, { animation: true, autohide: true, delay: 4500 });
            bsToast.show();
            toast.addEventListener('hidden.bs.toast', function () { toast.remove(); });
        } else {
            setTimeout(function () { toast.remove(); }, 4500);
        }
    }

    window.showAppToast = showAppToast;
})();

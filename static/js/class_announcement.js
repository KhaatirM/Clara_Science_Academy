/**
 * Class announcement modal: compose, broadcast target, and past announcements.
 */
(function () {
    'use strict';

    var panelData = null;
    var broadcastOptionsByValue = {};

    function escapeHtml(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function formatAnnouncementTime(iso) {
        if (!iso) return '';
        var date = new Date(iso);
        if (Number.isNaN(date.getTime())) return '';
        return date.toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        });
    }

    function truncateMessage(text, maxLen) {
        var msg = String(text || '');
        if (msg.length <= maxLen) return msg;
        return msg.slice(0, maxLen).trim() + '…';
    }

    function getModalEl() {
        return document.getElementById('classAnnouncementModal');
    }

    function getClassId() {
        var modal = getModalEl();
        if (!modal) return null;
        return parseInt(modal.getAttribute('data-class-id'), 10) || null;
    }

    function applyBroadcastSelection(value) {
        var targetGroupInput = document.getElementById('class-announcement-target-group');
        var classIdInput = document.getElementById('class-announcement-class-id');
        var hintEl = document.getElementById('class-announcement-broadcast-hint');
        var submitLabel = document.getElementById('class-announcement-submit-label');
        var opt = broadcastOptionsByValue[value];

        if (!targetGroupInput || !classIdInput) return;

        if (value === 'all_students') {
            targetGroupInput.value = 'all_students';
            classIdInput.value = '';
            classIdInput.removeAttribute('name');
            if (hintEl) hintEl.textContent = opt && opt.description ? opt.description : 'Delivered to every student in the school.';
            if (submitLabel) submitLabel.textContent = 'Send to all students';
        } else if (value && value.indexOf('class:') === 0) {
            var classId = value.split(':')[1];
            targetGroupInput.value = 'class';
            classIdInput.value = classId;
            classIdInput.setAttribute('name', 'class_id');
            if (hintEl) {
                hintEl.textContent = opt && opt.description
                    ? opt.description
                    : 'Delivered to students enrolled in this class.';
            }
            if (submitLabel) {
                submitLabel.textContent = opt && opt.is_current
                    ? 'Send to this class'
                    : 'Send to selected class';
            }
        }
    }

    function populateBroadcastSelect(options, defaultValue) {
        var select = document.getElementById('class-announcement-broadcast');
        if (!select) return;

        broadcastOptionsByValue = {};
        select.innerHTML = '';

        (options || []).forEach(function (opt) {
            broadcastOptionsByValue[opt.value] = opt;
            var optionEl = document.createElement('option');
            optionEl.value = opt.value;
            optionEl.textContent = opt.label;
            if (opt.value === defaultValue) {
                optionEl.selected = true;
            }
            select.appendChild(optionEl);
        });

        if (defaultValue) {
            applyBroadcastSelection(defaultValue);
        }
    }

    function renderPastAnnouncements(announcements) {
        var panel = document.getElementById('class-announcement-history-panel');
        var countBadge = document.getElementById('class-announcement-history-count');
        if (!panel) return;

        var list = announcements || [];
        if (countBadge) {
            countBadge.textContent = String(list.length);
        }

        if (!list.length) {
            panel.innerHTML =
                '<div class="class-announcement-history-empty">' +
                '<i class="bi bi-megaphone"></i>' +
                '<p class="mb-0">No announcements yet for this class.</p>' +
                '</div>';
            return;
        }

        var html = '<div class="class-announcement-history-list">';
        list.forEach(function (ann) {
            var importantClass = ann.is_important ? ' is-important' : '';
            var wideClass = ann.target_group === 'all_students' || ann.target_group === 'all' ? ' is-wide' : '';
            html +=
                '<article class="class-announcement-history-item' + importantClass + '">' +
                '<div class="class-announcement-history-item-header">' +
                '<h6 class="class-announcement-history-item-title">' + escapeHtml(ann.title) + '</h6>' +
                '<span class="class-announcement-history-item-meta">' + escapeHtml(formatAnnouncementTime(ann.timestamp)) + '</span>' +
                '</div>' +
                '<p class="class-announcement-history-item-message">' + escapeHtml(truncateMessage(ann.message, 220)) + '</p>' +
                '<div class="class-announcement-history-item-footer">' +
                '<span class="class-announcement-target-badge' + wideClass + '">' + escapeHtml(ann.target_label) + '</span>' +
                (ann.is_important ? '<span class="class-announcement-important-badge">Important</span>' : '') +
                '<span class="text-muted small ms-auto">' + escapeHtml(ann.sender_name) + '</span>' +
                '</div>' +
                '</article>';
        });
        html += '</div>';
        panel.innerHTML = html;
    }

    function updatePageAnnouncementsList(announcements) {
        var container = document.getElementById('class-page-announcements-list');
        if (!container) return;

        var list = (announcements || []).filter(function (ann) {
            var classId = getClassId();
            return ann.target_group === 'all_students' ||
                ann.target_group === 'all' ||
                (ann.class_id && classId && ann.class_id === classId);
        }).slice(0, 5);

        if (!list.length) {
            container.innerHTML =
                '<div class="teacher-class-empty-state">' +
                '<i class="bi bi-megaphone"></i>' +
                '<p>No recent announcements.</p>' +
                '</div>';
            return;
        }

        var html = '<div class="teacher-class-announcements">';
        list.forEach(function (ann) {
            html +=
                '<div class="teacher-class-announcement-item">' +
                '<div class="teacher-class-announcement-header">' +
                '<h6 class="teacher-class-announcement-title">' + escapeHtml(ann.title) + '</h6>' +
                '<small class="teacher-class-announcement-date">' + escapeHtml(formatAnnouncementTime(ann.timestamp)) + '</small>' +
                '</div>' +
                '<p class="teacher-class-announcement-message">' + escapeHtml(truncateMessage(ann.message, 100)) + '</p>' +
                '</div>';
        });
        html += '</div>';
        container.innerHTML = html;
    }

    function loadPanelData() {
        var classId = getClassId();
        var panel = document.getElementById('class-announcement-history-panel');
        if (!classId || !panel) return Promise.resolve();

        panel.innerHTML =
            '<div class="class-announcement-loading">' +
            '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>' +
            'Loading history…' +
            '</div>';

        return fetch('/communications/api/class-announcement-panel?class_id=' + encodeURIComponent(classId), {
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
            .then(function (response) {
                return response.json().then(function (data) {
                    return { ok: response.ok, data: data };
                });
            })
            .then(function (result) {
                if (!result.ok || !result.data || !result.data.success) {
                    throw new Error((result.data && result.data.message) || 'Could not load announcements.');
                }
                panelData = result.data;
                populateBroadcastSelect(result.data.broadcast_options, result.data.default_broadcast);
                renderPastAnnouncements(result.data.past_announcements);
                updatePageAnnouncementsList(result.data.past_announcements);
            })
            .catch(function (err) {
                panel.innerHTML =
                    '<div class="class-announcement-history-empty text-danger">' +
                    '<i class="bi bi-exclamation-circle"></i>' +
                    '<p class="mb-0">' + escapeHtml(err.message || 'Failed to load.') + '</p>' +
                    '</div>';
            });
    }

    function resetComposeForm() {
        var form = document.getElementById('class-announcement-form');
        if (!form) return;
        form.reset();
        if (panelData && panelData.default_broadcast) {
            var select = document.getElementById('class-announcement-broadcast');
            if (select) select.value = panelData.default_broadcast;
            applyBroadcastSelection(panelData.default_broadcast);
        }
    }

    function initClassAnnouncementForm() {
        var form = document.getElementById('class-announcement-form');
        var modalEl = getModalEl();
        if (!form || !modalEl) return;

        var broadcastSelect = document.getElementById('class-announcement-broadcast');
        if (broadcastSelect) {
            broadcastSelect.addEventListener('change', function () {
                applyBroadcastSelection(broadcastSelect.value);
            });
        }

        modalEl.addEventListener('shown.bs.modal', function () {
            loadPanelData();
        });

        modalEl.addEventListener('hidden.bs.modal', function () {
            resetComposeForm();
            var submitBtn = document.getElementById('class-announcement-submit');
            if (submitBtn) submitBtn.disabled = false;
        });

        form.addEventListener('submit', function (event) {
            event.preventDefault();

            if (broadcastSelect && broadcastSelect.value) {
                applyBroadcastSelection(broadcastSelect.value);
            }

            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }

            var submitBtn = document.getElementById('class-announcement-submit');
            var originalHtml = submitBtn ? submitBtn.innerHTML : '';
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML =
                    '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Sending…';
            }

            var formData = new FormData(form);
            if (!formData.get('is_important')) {
                formData.delete('is_important');
            }

            fetch('/communications/create-announcement', {
                method: 'POST',
                body: formData,
                credentials: 'same-origin',
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            })
                .then(function (response) {
                    var contentType = response.headers.get('content-type') || '';
                    if (contentType.indexOf('application/json') !== -1) {
                        return response.json().then(function (data) {
                            return { ok: response.ok, data: data };
                        });
                    }
                    throw new Error('Unexpected response from server.');
                })
                .then(function (result) {
                    if (result.ok && result.data && result.data.success) {
                        resetComposeForm();
                        if (typeof window.showAppToast === 'function') {
                            window.showAppToast('Announcement sent successfully.', 'success');
                        }
                        return loadPanelData();
                    }
                    var message = (result.data && result.data.message) || 'Could not send announcement.';
                    if (typeof window.showAppToast === 'function') {
                        window.showAppToast(message, 'error');
                    }
                })
                .catch(function () {
                    if (typeof window.showAppToast === 'function') {
                        window.showAppToast('Could not send announcement. Please try again.', 'error');
                    }
                })
                .finally(function () {
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalHtml;
                    }
                });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initClassAnnouncementForm);
    } else {
        initClassAnnouncementForm();
    }
})();

/**
 * Frontend Error Capture System
 * Automatically captures JavaScript errors and sends them to the backend
 */

(function() {
    'use strict';

    // Configuration
    const ERROR_ENDPOINT = '/api/frontend-error';
    const MAX_ERRORS_PER_SESSION = 10; // Prevent spam
    let errorCount = 0;

    // Error data structure
    function createErrorData(error, context = {}) {
        return {
            message: error.message || 'Unknown error',
            filename: error.filename || window.location.href,
            lineno: error.lineno || 0,
            colno: error.colno || 0,
            stack: error.stack || 'No stack trace available',
            url: window.location.href,
            userAgent: navigator.userAgent,
            timestamp: new Date().toISOString(),
            context: context
        };
    }

    // Send error to backend
    function sendErrorToBackend(errorData) {
        // Check if we've exceeded the error limit
        if (errorCount >= MAX_ERRORS_PER_SESSION) {
            console.warn('Maximum error limit reached for this session');
            return;
        }

        // Increment error count
        errorCount++;

        // Send error data to backend
        fetch(ERROR_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(errorData)
        }).catch(function(err) {
            console.error('Failed to send error report:', err);
        });
    }

    // Get CSRF token from meta tag or form
    function getCSRFToken() {
        const metaTag = document.querySelector('meta[name=csrf-token]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }
        
        const form = document.querySelector('form');
        if (form) {
            const csrfInput = form.querySelector('input[name=csrf_token]');
            if (csrfInput) {
                return csrfInput.value;
            }
        }
        
        return '';
    }

    // Global error handler
    window.addEventListener('error', function(event) {
        const errorData = createErrorData(event.error || event, {
            type: 'javascript_error',
            target: event.target ? event.target.tagName : 'unknown',
            filename: event.filename,
            lineno: event.lineno,
            colno: event.colno
        });

        console.error('JavaScript Error Captured:', errorData);
        sendErrorToBackend(errorData);
    });

    // Unhandled promise rejection handler
    window.addEventListener('unhandledrejection', function(event) {
        const errorData = createErrorData(new Error(event.reason), {
            type: 'unhandled_promise_rejection',
            reason: event.reason
        });

        console.error('Unhandled Promise Rejection Captured:', errorData);
        sendErrorToBackend(errorData);
    });

    // AJAX error handler
    function setupAjaxErrorHandling() {
        // Override fetch to catch errors
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            return originalFetch.apply(this, args)
                .catch(function(error) {
                    const errorData = createErrorData(error, {
                        type: 'fetch_error',
                        url: args[0],
                        options: args[1]
                    });
                    
                    console.error('Fetch Error Captured:', errorData);
                    sendErrorToBackend(errorData);
                    
                    throw error; // Re-throw to maintain normal error handling
                });
        };

        // Override XMLHttpRequest to catch errors
        const originalXHROpen = XMLHttpRequest.prototype.open;
        const originalXHRSend = XMLHttpRequest.prototype.send;

        XMLHttpRequest.prototype.open = function(method, url, ...args) {
            this._method = method;
            this._url = url;
            return originalXHROpen.apply(this, [method, url, ...args]);
        };

        XMLHttpRequest.prototype.send = function(data) {
            const xhr = this;
            
            xhr.addEventListener('error', function() {
                const errorData = createErrorData(new Error('XMLHttpRequest failed'), {
                    type: 'xhr_error',
                    method: xhr._method,
                    url: xhr._url,
                    status: xhr.status,
                    statusText: xhr.statusText
                });
                
                console.error('XHR Error Captured:', errorData);
                sendErrorToBackend(errorData);
            });

            return originalXHRSend.apply(this, arguments);
        };
    }

    // Form validation error handler
    function setupFormErrorHandling() {
        document.addEventListener('submit', function(event) {
            const form = event.target;
            if (form.checkValidity && !form.checkValidity()) {
                const errorData = createErrorData(new Error('Form validation failed'), {
                    type: 'form_validation_error',
                    formId: form.id || 'unknown',
                    formAction: form.action || 'unknown'
                });
                
                console.error('Form Validation Error Captured:', errorData);
                sendErrorToBackend(errorData);
            }
        });
    }

    // Performance monitoring
    function setupPerformanceMonitoring() {
        // Monitor long tasks
        if ('PerformanceObserver' in window) {
            try {
                const observer = new PerformanceObserver(function(list) {
                    for (const entry of list.getEntries()) {
                        if (entry.duration > 200) { // Tasks longer than 200ms
                            const errorData = createErrorData(new Error('Long task detected'), {
                                type: 'performance_issue',
                                duration: entry.duration,
                                startTime: entry.startTime,
                                name: entry.name
                            });
                            
                            console.warn('Performance Issue Detected:', errorData);
                            sendErrorToBackend(errorData);
                        }
                    }
                });
                
                observer.observe({ entryTypes: ['longtask'] });
            } catch (e) {
                console.warn('Performance monitoring not supported:', e);
            }
        }
    }

    // Initialize error capture when DOM is ready
    function initializeErrorCapture() {
        setupAjaxErrorHandling();
        setupFormErrorHandling();
        setupPerformanceMonitoring();
        
        console.log('Frontend error capture system initialized');
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeErrorCapture);
    } else {
        initializeErrorCapture();
    }

    // Manual error reporting function
    window.reportError = function(error, context = {}) {
        const errorData = createErrorData(error, {
            type: 'manual_error_report',
            ...context
        });
        
        console.error('Manual Error Report:', errorData);
        sendErrorToBackend(errorData);
    };

    // Test function for debugging
    window.testErrorCapture = function() {
        try {
            throw new Error('Test error for error capture system');
        } catch (e) {
            window.reportError(e, { type: 'test_error' });
        }
    };

})();

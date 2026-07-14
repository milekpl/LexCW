/**
 * Handles authentication failures centrally, for every request.
 *
 * A 401/403 is never something a call site should be interpreting. When it is
 * left to them, they get it wrong in a specific and confusing way: a handler
 * written as
 *
 *     fetch(url).then(r => r.json()).then(data => { ... })
 *
 * never looks at the status, so it parses the *error* body as if it were a
 * result and reports a domain failure. That is exactly how a 401 on
 * /api/pronunciation/draft surfaced to the user as "ByT5 model not available" —
 * sending us hunting a machine-learning bug that did not exist. 36 such call
 * sites across 7 files have no status check at all.
 *
 * So the auth cases are handled here, once:
 *
 *   401 -> the session is gone. Redirect to the login page, preserving the
 *          current page as ?next= so the user lands back where they were.
 *   403 -> authenticated but not permitted. Surface the server's own message
 *          (the error contract in app/utils/auth_decorators.py always supplies
 *          one) rather than a guess.
 *
 * In both cases the fetch promise rejects, so a handler that skips the status
 * check cannot go on to parse the error body as data.
 *
 * Requests may opt out with the X-Auth-Silent header — used by probes like
 * /api/auth/check whose whole job is to *ask* whether you are signed in.
 *
 * Loaded from base.html after csrf.js (which wraps the same two transports to
 * attach the CSRF token; the wrappers compose).
 */
(function () {
  'use strict';

  var LOGIN_PATH = '/auth/login';
  var SILENT_HEADER = 'x-auth-silent';

  function isOnAuthPage() {
    // Never bounce the login page to itself.
    return window.location.pathname.indexOf('/auth/') === 0;
  }

  function isSameOrigin(url) {
    try {
      return new URL(url, window.location.href).origin === window.location.origin;
    } catch (err) {
      return false;
    }
  }

  function redirectToLogin() {
    if (isOnAuthPage()) {
      return;
    }
    var next = window.location.pathname + window.location.search;
    window.location.assign(LOGIN_PATH + '?next=' + encodeURIComponent(next));
  }

  function messageFrom(bodyText, fallback) {
    try {
      var body = JSON.parse(bodyText);
      if (body && body.error) {
        return body.error;
      }
    } catch (err) {
      /* Not JSON (an HTML error page, say) — fall through. */
    }
    return fallback;
  }

  /** Acts on an auth failure and returns the Error to reject the request with. */
  function handleAuthFailure(status, bodyText) {
    if (status === 401) {
      redirectToLogin();
      return new Error(messageFrom(bodyText, 'Not signed in.'));
    }

    var message = messageFrom(bodyText, 'You do not have permission to do that.');
    if (typeof showToast === 'function') {
      showToast(message, 'warning');
    }
    return new Error(message);
  }

  function isAuthFailure(status) {
    return status === 401 || status === 403;
  }

  function isSilent(headers) {
    if (!headers) {
      return false;
    }
    if (typeof Headers !== 'undefined' && headers instanceof Headers) {
      return headers.has(SILENT_HEADER);
    }
    return Object.keys(headers).some(function (key) {
      return key.toLowerCase() === SILENT_HEADER;
    });
  }

  var nativeFetch = window.fetch;
  if (typeof nativeFetch === 'function') {
    window.fetch = function (input, init) {
      var options = init || {};
      var isRequest = typeof Request !== 'undefined' && input instanceof Request;
      var url = isRequest ? input.url : String(input);
      var headers = options.headers || (isRequest ? input.headers : null);
      var silent = isSilent(headers);

      return nativeFetch.call(this, input, init).then(function (response) {
        if (!isAuthFailure(response.status) || silent || !isSameOrigin(url)) {
          return response;
        }
        // clone(): leave the caller's body readable if they catch and inspect it.
        return response.clone().text().then(function (text) {
          throw handleAuthFailure(response.status, text);
        });
      });
    };
  }

  var nativeOpen = XMLHttpRequest.prototype.open;
  var nativeSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function (method, url) {
    this.__authSameOrigin = isSameOrigin(url);
    return nativeOpen.apply(this, arguments);
  };

  XMLHttpRequest.prototype.send = function () {
    var xhr = this;
    xhr.addEventListener('load', function () {
      if (isAuthFailure(xhr.status) && xhr.__authSameOrigin) {
        handleAuthFailure(xhr.status, xhr.responseText);
      }
    });
    return nativeSend.apply(this, arguments);
  };
})();

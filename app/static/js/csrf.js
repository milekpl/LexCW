/**
 * Attaches the CSRF token to every state-changing same-origin request.
 *
 * The server enforces one rule with no per-endpoint exemptions: a cookie-
 * authenticated POST/PUT/PATCH/DELETE must carry a CSRF token (Bearer-
 * authenticated requests are exempt, since a token in a header is not an ambient
 * credential). Rather than ask 30-odd call sites to remember a header — which is
 * how the previous patchwork of server-side exemptions accumulated — this wraps
 * fetch and XMLHttpRequest once, so any request from any script is covered,
 * including scripts not yet written.
 *
 * Call sites that already set the header keep working; theirs is left in place.
 *
 * Must load before any script that issues requests.
 */
(function () {
  'use strict';

  var meta = document.querySelector('meta[name="csrf-token"]');
  var TOKEN = meta ? meta.getAttribute('content') : '';
  if (!TOKEN) {
    return; // No token rendered (e.g. login page before a session exists).
  }

  // Mirrors Flask-WTF's WTF_CSRF_METHODS.
  var UNSAFE_METHOD = /^(POST|PUT|PATCH|DELETE)$/i;
  var HEADER = 'X-CSRFToken'; // One of Flask-WTF's default WTF_CSRF_HEADERS.

  function isSameOrigin(url) {
    try {
      return new URL(url, window.location.href).origin === window.location.origin;
    } catch (err) {
      return false; // Unparseable URL: treat as cross-origin and add nothing.
    }
  }

  function needsToken(method, url) {
    return UNSAFE_METHOD.test(method || 'GET') && isSameOrigin(url);
  }

  var nativeFetch = window.fetch;
  if (typeof nativeFetch === 'function') {
    window.fetch = function (input, init) {
      var options = init || {};
      var isRequest = typeof Request !== 'undefined' && input instanceof Request;
      var url = isRequest ? input.url : String(input);
      var method = options.method || (isRequest ? input.method : 'GET');

      if (needsToken(method, url)) {
        var headers = new Headers(options.headers || (isRequest ? input.headers : undefined));
        if (!headers.has(HEADER)) {
          headers.set(HEADER, TOKEN);
        }
        options = Object.assign({}, options, { headers: headers });
      }

      return nativeFetch.call(this, input, options);
    };
  }

  var nativeOpen = XMLHttpRequest.prototype.open;
  var nativeSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function (method, url) {
    this.__csrfNeedsToken = needsToken(method, url);
    return nativeOpen.apply(this, arguments);
  };

  XMLHttpRequest.prototype.send = function () {
    if (this.__csrfNeedsToken) {
      try {
        this.setRequestHeader(HEADER, TOKEN);
      } catch (err) {
        /* Header already set, or send() called in a bad state — leave it alone. */
      }
    }
    return nativeSend.apply(this, arguments);
  };
})();

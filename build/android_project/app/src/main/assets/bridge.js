
/*
 * bridge.js  —  Android WebView helper
 * Developed by BALAVIGNESH A
 *
 * Injected into every page after load.
 * Provides:
 *   1. window.open() -> Android.openPreview(html)  (Live Preview)
 *   2. <a download href="blob:..."> -> Android.downloadBase64()
 *   3. <a download href="data:..."> -> Android.downloadBase64()
 */
(function () {
  'use strict';

  /* ── 1. Patch window.open ──────────────────────────────────── */
  var _origOpen = window.open;

  window.open = function (url, target, features) {
    /* No URL or blank — caller will document.write() into returned window */
    if (!url || url === '' || url === 'about:blank') {
      var captured = '';
      var fakeWin = {
        document: {
          write:   function (h) { captured += h; },
          writeln: function (h) { captured += h + '\n'; },
          close:   function ()  {
            if (typeof Android !== 'undefined') {
              Android.openPreview(captured);
            }
          }
        },
        close: function () {}
      };
      return fakeWin;
    }

    /* blob: URL — fetch HTML text and preview it */
    if (url.indexOf('blob:') === 0) {
      fetch(url)
        .then(function (r) { return r.text(); })
        .then(function (html) {
          if (typeof Android !== 'undefined') {
            Android.openPreview(html);
          }
        })
        .catch(function () {
          _origOpen.call(window, url, target, features);
        });
      return null;
    }

    /* Anything else (http / https) — open inside WebView as normal */
    return _origOpen.call(window, url, target, features);
  };

  /* ── 2. Intercept <a download> clicks ─────────────────────── */
  document.addEventListener('click', function (e) {
    /* Walk up the DOM to find an <a download> ancestor */
    var node = e.target;
    while (node && node.tagName !== 'A') {
      node = node.parentElement;
    }
    if (!node || !node.hasAttribute('download')) return;

    var href  = node.href  || '';
    var fname = node.getAttribute('download') || 'download';
    if (!fname || fname.trim() === '') fname = 'download';

    /* blob: href */
    if (href.indexOf('blob:') === 0) {
      e.preventDefault();
      e.stopPropagation();
      fetch(href)
        .then(function (r) { return r.blob(); })
        .then(function (b) {
          var reader = new FileReader();
          reader.onload = function () {
            if (typeof Android !== 'undefined') {
              Android.downloadBase64(
                reader.result,
                fname,
                b.type || 'application/octet-stream'
              );
            }
          };
          reader.readAsDataURL(b);
        })
        .catch(function (err) {
          if (typeof Android !== 'undefined') {
            Android.showToast('Download error: ' + err);
          }
        });
      return;
    }

    /* data: href */
    if (href.indexOf('data:') === 0) {
      e.preventDefault();
      e.stopPropagation();
      if (typeof Android !== 'undefined') {
        Android.downloadBase64(href, fname, '');
      }
    }
  }, true);

})();

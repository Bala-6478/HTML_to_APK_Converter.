package com.bala.mywebapp;

import android.annotation.SuppressLint;
import android.app.AlertDialog;
import android.content.ContentValues;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Base64;
import android.util.Log;
import android.webkit.JsPromptResult;
import android.webkit.JsResult;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.webkit.WebSettingsCompat;
import androidx.webkit.WebViewFeature;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * MainActivity — HTML to APK Builder v3.0
 * Developed by BALAVIGNESH A
 *
 * Key features:
 *   - Loads index.html from assets via WebView
 *   - Injects bridge.js (assets/bridge.js) after every page load
 *   - AndroidBridge exposes downloadBase64 / downloadText / openPreview / showToast to JS
 *   - DownloadListener handles blob:, data:, and https: downloads
 *   - window.open() is patched in bridge.js -> openPreview() shows a full-screen dialog
 *   - No runtime permission dialogs (all pre-declared in AndroidManifest)
 */
public class MainActivity extends AppCompatActivity {

    private static final String TAG = "APKBuilder";
    private WebView webView;
    private ValueCallback<Uri[]> mFilePathCallback;
    private String bridgeJs = null;   // loaded once from assets/bridge.js

    // =========================================================
    // JavaScript -> Java bridge
    // =========================================================
    public class AndroidBridge {

        /** Download a base64 data string (or data URI) as a file. */
        @android.webkit.JavascriptInterface
        public void downloadBase64(String base64Data, String fileName, String mimeType) {
            Log.d(TAG, "downloadBase64: " + fileName);
            try {
                byte[] bytes;
                if (base64Data.contains(",")) {
                    String pure = base64Data.substring(base64Data.indexOf(",") + 1);
                    bytes = Base64.decode(pure, Base64.DEFAULT);
                } else {
                    bytes = Base64.decode(base64Data, Base64.DEFAULT);
                }
                saveBytes(bytes, fileName, mimeType);
            } catch (Exception e) {
                Log.e(TAG, "downloadBase64 failed", e);
                showToastOnUi("Download failed: " + e.getMessage());
            }
        }

        /** Download a plain UTF-8 text string as a file. */
        @android.webkit.JavascriptInterface
        public void downloadText(String text, String fileName, String mimeType) {
            Log.d(TAG, "downloadText: " + fileName);
            try {
                byte[] bytes = text.getBytes("UTF-8");
                String safeName = (fileName != null && !fileName.isEmpty()) ? fileName : "download.txt";
                String safeMime = (mimeType != null && !mimeType.isEmpty()) ? mimeType : "text/plain";
                saveBytes(bytes, safeName, safeMime);
            } catch (Exception e) {
                Log.e(TAG, "downloadText failed", e);
                showToastOnUi("Download failed: " + e.getMessage());
            }
        }

        /** Show a native Android Toast from JavaScript. */
        @android.webkit.JavascriptInterface
        public void showToast(String message) {
            showToastOnUi(message);
        }

        /** Open an HTML string as a full-screen live preview dialog. */
        @android.webkit.JavascriptInterface
        public void openPreview(String htmlContent) {
            Log.d(TAG, "openPreview: " + (htmlContent != null ? htmlContent.length() : 0) + " chars");
            final String html = htmlContent;
            runOnUiThread(new Runnable() {
                @Override public void run() { showPreviewDialog(html); }
            });
        }
    }

    // =========================================================
    // onCreate
    // =========================================================
    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // Load bridge.js once from assets
        bridgeJs = loadAssetText("bridge.js");

        webView = findViewById(R.id.webview);
        WebSettings s = webView.getSettings();

        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setAllowFileAccessFromFileURLs(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setSupportZoom(true);
        s.setBuiltInZoomControls(true);
        s.setDisplayZoomControls(false);
        s.setTextZoom(100);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        // Dark mode: let the HTML handle its own theming
        if (WebViewFeature.isFeatureSupported(WebViewFeature.FORCE_DARK)) {
            WebSettingsCompat.setForceDark(s, WebSettingsCompat.FORCE_DARK_OFF);
        }

        // Attach the JS <-> Java bridge
        webView.addJavascriptInterface(new AndroidBridge(), "Android");

        // WebViewClient
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String url = request.getUrl().toString();
                // blob: URLs cannot be navigated to — intercept via JS evaluation
                if (url.startsWith("blob:")) {
                    interceptBlobDownload(url);
                    return true;
                }
                return false; // load everything else inside the WebView
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                // Inject bridge.js after every page load
                if (bridgeJs != null && !bridgeJs.isEmpty()) {
                    view.evaluateJavascript(bridgeJs, null);
                }
            }
        });

        // WebChromeClient — file chooser + JS dialogs
        webView.setWebChromeClient(new WebChromeClient() {

            @Override
            public boolean onShowFileChooser(WebView wv,
                    ValueCallback<Uri[]> filePathCallback,
                    FileChooserParams fileChooserParams) {
                if (mFilePathCallback != null) {
                    mFilePathCallback.onReceiveValue(null);
                }
                mFilePathCallback = filePathCallback;
                Intent intent = fileChooserParams.createIntent();
                try {
                    startActivityForResult(intent, 1001);
                } catch (Exception e) {
                    mFilePathCallback = null;
                    return false;
                }
                return true;
            }

            @Override
            public boolean onJsAlert(WebView view, String url, String message, JsResult result) {
                new AlertDialog.Builder(MainActivity.this)
                    .setMessage(message)
                    .setPositiveButton("OK", (d, w) -> result.confirm())
                    .setOnCancelListener(d -> result.cancel())
                    .show();
                return true;
            }

            @Override
            public boolean onJsConfirm(WebView view, String url, String message, JsResult result) {
                new AlertDialog.Builder(MainActivity.this)
                    .setMessage(message)
                    .setPositiveButton("OK",     (d, w) -> result.confirm())
                    .setNegativeButton("Cancel", (d, w) -> result.cancel())
                    .setOnCancelListener(d -> result.cancel())
                    .show();
                return true;
            }

            @Override
            public boolean onJsPrompt(WebView view, String url, String message,
                                      String defaultValue, JsPromptResult result) {
                android.widget.EditText input = new android.widget.EditText(MainActivity.this);
                input.setText(defaultValue);
                new AlertDialog.Builder(MainActivity.this)
                    .setMessage(message)
                    .setView(input)
                    .setPositiveButton("OK",     (d, w) -> result.confirm(input.getText().toString()))
                    .setNegativeButton("Cancel", (d, w) -> result.cancel())
                    .setOnCancelListener(d -> result.cancel())
                    .show();
                return true;
            }
        });

        // DownloadListener — catches blob:, data:, https: downloads
        webView.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> {
            Log.d(TAG, "DownloadListener: " + url.substring(0, Math.min(60, url.length())));
            if (url.startsWith("data:")) {
                handleDataUriDownload(url, mimeType, contentDisposition);
            } else if (url.startsWith("blob:")) {
                interceptBlobDownload(url);
            } else {
                downloadUrlInBackground(url, userAgent, mimeType, contentDisposition);
            }
        });

        webView.loadUrl("file:///android_asset/index.html");
    }

    // =========================================================
    // Live Preview dialog
    // =========================================================
    private void showPreviewDialog(String htmlContent) {
        WebView preview = new WebView(this);
        WebSettings ps = preview.getSettings();
        ps.setJavaScriptEnabled(true);
        ps.setDomStorageEnabled(true);
        ps.setAllowFileAccess(true);
        ps.setAllowUniversalAccessFromFileURLs(true);
        ps.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        preview.setWebViewClient(new WebViewClient());

        String html = (htmlContent != null && !htmlContent.trim().isEmpty())
            ? htmlContent : "<html><body><p>Empty preview</p></body></html>";

        preview.loadDataWithBaseURL(
            "file:///android_asset/",
            html,
            "text/html",
            "UTF-8",
            null
        );

        FrameLayout container = new FrameLayout(this);
        FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.MATCH_PARENT
        );
        preview.setLayoutParams(lp);
        container.addView(preview);

        AlertDialog dlg = new AlertDialog.Builder(this)
            .setTitle("Live Preview")
            .setView(container)
            .setPositiveButton("Close", null)
            .create();
        dlg.show();
        if (dlg.getWindow() != null) {
            dlg.getWindow().setLayout(
                android.view.WindowManager.LayoutParams.MATCH_PARENT,
                (int)(getResources().getDisplayMetrics().heightPixels * 0.92)
            );
        }
    }

    // =========================================================
    // Download helpers
    // =========================================================

    /** Use JS evaluation to fetch a blob: URL and hand bytes to AndroidBridge. */
    private void interceptBlobDownload(String blobUrl) {
        String escaped = blobUrl.replace("\\", "\\\\").replace("'", "\\'");
        String js =
            "(function(){" +
            "  fetch('" + escaped + "')" +
            "    .then(function(r){ return r.blob(); })" +
            "    .then(function(b){" +
            "      var rd = new FileReader();" +
            "      rd.onload = function(){" +
            "        if(typeof Android!=='undefined')" +
            "          Android.downloadBase64(rd.result,'download',b.type||'application/octet-stream');" +
            "      };" +
            "      rd.readAsDataURL(b);" +
            "    })" +
            "    .catch(function(e){ if(typeof Android!=='undefined') Android.showToast('Blob error: '+e); });" +
            "})();";
        webView.evaluateJavascript(js, null);
    }

    private void handleDataUriDownload(String dataUri, String mimeType, String contentDisposition) {
        new Thread(() -> {
            try {
                String[] parts = dataUri.split(",", 2);
                String header  = parts[0];
                String body    = parts.length > 1 ? parts[1] : "";
                String mime    = (mimeType != null && !mimeType.isEmpty()) ? mimeType
                    : (header.contains(":") ? header.split(":")[1].split(";")[0] : "application/octet-stream");
                String ext     = extensionForMime(mime);
                String fname   = extractFilename(contentDisposition, "download" + ext);
                byte[] bytes;
                if (header.contains("base64")) {
                    bytes = Base64.decode(body, Base64.DEFAULT);
                } else {
                    bytes = java.net.URLDecoder.decode(body, "UTF-8").getBytes("UTF-8");
                }
                saveBytes(bytes, fname, mime);
            } catch (Exception e) {
                Log.e(TAG, "data URI download failed", e);
                showToastOnUi("Download failed: " + e.getMessage());
            }
        }).start();
    }

    private void downloadUrlInBackground(String urlStr, String userAgent, String mimeType, String contentDisposition) {
        new Thread(() -> {
            try {
                URL url = new URL(urlStr);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestProperty("User-Agent", userAgent != null ? userAgent : "Android");
                conn.connect();
                String cd   = conn.getHeaderField("Content-Disposition");
                String ct   = conn.getHeaderField("Content-Type");
                String mime = (ct != null && !ct.isEmpty()) ? ct.split(";")[0].trim()
                    : (mimeType != null ? mimeType : "application/octet-stream");
                String fname = extractFilename(cd != null ? cd : contentDisposition,
                    "download" + extensionForMime(mime));
                ByteArrayOutputStream baos = new ByteArrayOutputStream();
                InputStream is = conn.getInputStream();
                byte[] buf = new byte[8192];
                int n;
                while ((n = is.read(buf)) != -1) baos.write(buf, 0, n);
                is.close();
                conn.disconnect();
                saveBytes(baos.toByteArray(), fname, mime);
            } catch (Exception e) {
                Log.e(TAG, "URL download failed", e);
                showToastOnUi("Download failed: " + e.getMessage());
            }
        }).start();
    }

    /**
     * Save bytes to Downloads folder.
     * Android 10+ -> MediaStore (Scoped Storage, no permission dialog).
     * Android 7-9 -> direct file write.
     */
    private void saveBytes(byte[] bytes, String fileName, String mimeType) {
        try {
            String safeMime = (mimeType != null && !mimeType.isEmpty()) ? mimeType : "application/octet-stream";
            String safeFile = (fileName != null && !fileName.trim().isEmpty()) ? fileName.trim() : "download.bin";

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                ContentValues cv = new ContentValues();
                cv.put(MediaStore.Downloads.DISPLAY_NAME, safeFile);
                cv.put(MediaStore.Downloads.MIME_TYPE, safeMime);
                cv.put(MediaStore.Downloads.IS_PENDING, 1);
                Uri col = MediaStore.Downloads.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY);
                Uri uri = getContentResolver().insert(col, cv);
                if (uri != null) {
                    try (OutputStream os = getContentResolver().openOutputStream(uri)) {
                        if (os != null) os.write(bytes);
                    }
                    cv.clear();
                    cv.put(MediaStore.Downloads.IS_PENDING, 0);
                    getContentResolver().update(uri, cv, null, null);
                    showToastOnUi("Saved to Downloads: " + safeFile);
                }
            } else {
                File dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
                dir.mkdirs();
                File out = new File(dir, safeFile);
                try (FileOutputStream fos = new FileOutputStream(out)) {
                    fos.write(bytes);
                }
                showToastOnUi("Saved: " + out.getAbsolutePath());
            }
        } catch (Exception e) {
            Log.e(TAG, "saveBytes failed", e);
            showToastOnUi("Save failed: " + e.getMessage());
        }
    }

    // =========================================================
    // Utility helpers
    // =========================================================

    private void showToastOnUi(String message) {
        runOnUiThread(() -> Toast.makeText(this, message, Toast.LENGTH_LONG).show());
    }

    /** Read a text file from assets/ into a String. */
    private String loadAssetText(String assetName) {
        try (InputStream is = getAssets().open(assetName);
             BufferedReader br = new BufferedReader(new InputStreamReader(is, "UTF-8"))) {
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = br.readLine()) != null) {
                sb.append(line).append('\n');
            }
            return sb.toString();
        } catch (Exception e) {
            Log.e(TAG, "Failed to load asset: " + assetName, e);
            return null;
        }
    }

    private String extensionForMime(String mime) {
        if (mime == null) return ".bin";
        switch (mime.trim().toLowerCase().split(";")[0].trim()) {
            case "text/html":              return ".html";
            case "text/plain":              return ".txt";
            case "text/css":               return ".css";
            case "text/javascript":
            case "application/javascript": return ".js";
            case "application/json":       return ".json";
            case "application/pdf":        return ".pdf";
            case "application/zip":        return ".zip";
            case "image/png":              return ".png";
            case "image/jpeg":             return ".jpg";
            case "image/gif":              return ".gif";
            case "image/svg+xml":          return ".svg";
            default:                       return ".bin";
        }
    }

    private String extractFilename(String contentDisposition, String fallback) {
        if (contentDisposition != null) {
            java.util.regex.Matcher m = java.util.regex.Pattern
                .compile("filename\\*?=[\"']?([^\"';\\n]+)[\"']?",
                         java.util.regex.Pattern.CASE_INSENSITIVE)
                .matcher(contentDisposition);
            if (m.find()) return m.group(1).trim();
        }
        return (fallback != null) ? fallback : "download.bin";
    }

    // =========================================================
    // File chooser result
    // =========================================================
    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == 1001) {
            if (mFilePathCallback == null) return;
            Uri[] results = null;
            if (resultCode == RESULT_OK && data != null) {
                if (data.getClipData() != null) {
                    int count = data.getClipData().getItemCount();
                    results = new Uri[count];
                    for (int i = 0; i < count; i++) {
                        results[i] = data.getClipData().getItemAt(i).getUri();
                    }
                } else if (data.getDataString() != null) {
                    results = new Uri[]{Uri.parse(data.getDataString())};
                }
            }
            mFilePathCallback.onReceiveValue(results);
            mFilePathCallback = null;
        }
    }

    // =========================================================
    // Back button
    // =========================================================
    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}

"""
HTML → APK Builder
Developed by BALAVIGNESH A
Converts a single-file HTML project into an installable Android APK.
"""

import os
import re
import sys
import shutil
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────────────
APP_NAME     = "MyWebApp"
PACKAGE_NAME = "com.bala.generatedapp"
VERSION_CODE = 1
VERSION_NAME = "1.0"
MIN_SDK      = 21   # Android 5.0+
TARGET_SDK   = 34   # Android 14

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
INPUT_HTML   = BASE_DIR / "input_project" / "index.html"
BUILD_DIR    = BASE_DIR / "build" / "android_project"
OUTPUT_DIR   = BASE_DIR / "output"
LOGS_DIR     = BASE_DIR / "logs"

# ─── Logging Setup ────────────────────────────────────────────────────────────
LOGS_DIR.mkdir(parents=True, exist_ok=True)
log_filename = LOGS_DIR / f"build_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. HTML ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_html(html: str) -> dict:
    """Detect HTML features that require specific Android permissions or settings."""
    features = {
        "internet":       bool(re.search(r'fetch\(|XMLHttpRequest|https?://', html, re.I)),
        "local_storage":  bool(re.search(r'localStorage|sessionStorage', html)),
        "drag_drop":      bool(re.search(r'draggable|ondragstart|ondrop|addEventListener.*drag', html, re.I)),
        "iframe":         bool(re.search(r'<iframe', html, re.I)),
        "file_picker":    bool(re.search(r'<input[^>]+type=["\']file["\']', html, re.I)),
        "media":          bool(re.search(r'<video|<audio', html, re.I)),
        "dark_mode":      bool(re.search(r'prefers-color-scheme|data-theme', html, re.I)),
        "geolocation":    bool(re.search(r'navigator\.geolocation', html, re.I)),
        "camera":         bool(re.search(r'getUserMedia|mediaDevices', html, re.I)),
        "vibration":      bool(re.search(r'navigator\.vibrate', html, re.I)),
        "notifications":  bool(re.search(r'Notification\.request|serviceWorker', html, re.I)),
    }
    log.info("HTML feature detection:")
    for k, v in features.items():
        log.info(f"  {k:<18} {'YES' if v else 'no'}")
    return features


# ═══════════════════════════════════════════════════════════════════════════════
# 2. ANDROID PROJECT GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

PACKAGE_PATH = PACKAGE_NAME.replace(".", "/")

# ── 2a. AndroidManifest.xml ──────────────────────────────────────────────────

def build_manifest(features: dict) -> str:
    permissions = []
    if features["internet"] or features["file_picker"] or features["notifications"]:
        permissions.append('<uses-permission android:name="android.permission.INTERNET"/>')
    if features["geolocation"]:
        permissions.append('<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>')
        permissions.append('<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>')
    if features["camera"]:
        permissions.append('<uses-permission android:name="android.permission.CAMERA"/>')
    if features["vibration"]:
        permissions.append('<uses-permission android:name="android.permission.VIBRATE"/>')

    perm_block = "\n    ".join(permissions)

    return f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{PACKAGE_NAME}">

    {perm_block}

    <application
        android:allowBackup="true"
        android:label="{APP_NAME}"
        android:supportsRtl="true"
        android:hardwareAccelerated="true"
        android:usesCleartextTraffic="true"
        android:theme="@style/AppTheme">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize|keyboardHidden"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>

    </application>
</manifest>
"""

# ── 2b. MainActivity.java ────────────────────────────────────────────────────

def build_main_activity(features: dict) -> str:
    imports = [
        "import android.app.Activity;",
        "import android.os.Bundle;",
        "import android.webkit.*;",
        "import android.view.View;",
        "import android.view.Window;",
    ]
    extra_imports = []
    file_chooser_code = ""
    js_interface_code = ""
    back_press_code = ""

    if features["file_picker"]:
        extra_imports += [
            "import android.content.Intent;",
            "import android.net.Uri;",
            "import android.webkit.ValueCallback;",
        ]
        file_chooser_code = """
    private ValueCallback<Uri[]> mFilePathCallback;
    private static final int FILE_CHOOSER_REQUEST = 100;

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == FILE_CHOOSER_REQUEST) {
            if (mFilePathCallback != null) {
                Uri[] results = null;
                if (resultCode == Activity.RESULT_OK && data != null) {
                    results = new Uri[]{data.getData()};
                }
                mFilePathCallback.onReceiveValue(results);
                mFilePathCallback = null;
            }
        }
        super.onActivityResult(requestCode, resultCode, data);
    }
"""

    if features["dark_mode"]:
        js_interface_code = """
        // Inject system dark-mode flag into the WebView
        webView.evaluateJavascript(
            "document.documentElement.setAttribute('data-theme'," +
            "(window.matchMedia('(prefers-color-scheme: dark)').matches ? '\"dark\"' : '\"light\"') + ");",
            null
        );
"""

    chrome_client_override = ""
    if features["file_picker"]:
        chrome_client_override = """
                    @Override
                    public boolean onShowFileChooser(WebView view,
                            ValueCallback<Uri[]> callback,
                            WebChromeClient.FileChooserParams params) {
                        mFilePathCallback = callback;
                        Intent intent = params.createIntent();
                        startActivityForResult(Intent.createChooser(intent, "Choose a file"), FILE_CHOOSER_REQUEST);
                        return true;
                    }
"""

    back_press_code = """
    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
"""

    all_imports = "\n".join(imports + extra_imports)

    return f"""package {PACKAGE_NAME};

{all_imports}

public class MainActivity extends Activity {{

    private WebView webView;
{file_chooser_code}
    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        setContentView(R.layout.activity_main);

        webView = findViewById(R.id.webview);

        // ── WebSettings ───────────────────────────────────────
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setBuiltInZoomControls(false);
        settings.setSupportZoom(false);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        // ── WebViewClient ─────────────────────────────────────
        webView.setWebViewClient(new WebViewClient() {{
            @Override
            public void onPageFinished(WebView view, String url) {{
                super.onPageFinished(view, url);
{js_interface_code}
            }}
        }});

        // ── WebChromeClient ───────────────────────────────────
        webView.setWebChromeClient(new WebChromeClient() {{
{chrome_client_override}
        }});

        webView.loadUrl("file:///android_asset/index.html");
    }}

{back_press_code}

    @Override
    protected void onPause() {{
        super.onPause();
        webView.onPause();
    }}

    @Override
    protected void onResume() {{
        super.onResume();
        webView.onResume();
    }}
}}
"""

# ── 2c. Layout XML ───────────────────────────────────────────────────────────

ACTIVITY_MAIN_XML = """<?xml version="1.0" encoding="utf-8"?>
<RelativeLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <WebView
        android:id="@+id/webview"
        android:layout_width="match_parent"
        android:layout_height="match_parent"/>

</RelativeLayout>
"""

# ── 2d. Styles / Resources ───────────────────────────────────────────────────

STYLES_XML = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="AppTheme" parent="android:Theme.Material.NoTitleBar.Fullscreen">
        <item name="android:windowBackground">@android:color/white</item>
        <item name="android:statusBarColor">@android:color/transparent</item>
    </style>
</resources>
"""

STRINGS_XML = f"""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">{APP_NAME}</string>
</resources>
"""

# ── 2e. Gradle files ─────────────────────────────────────────────────────────

APP_BUILD_GRADLE = f"""plugins {{
    id 'com.android.application'
}}

android {{
    namespace '{PACKAGE_NAME}'
    compileSdk {TARGET_SDK}

    defaultConfig {{
        applicationId "{PACKAGE_NAME}"
        minSdk {MIN_SDK}
        targetSdk {TARGET_SDK}
        versionCode {VERSION_CODE}
        versionName "{VERSION_NAME}"
    }}

    buildTypes {{
        release {{
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }}
    }}

    compileOptions {{
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }}
}}

dependencies {{
    implementation 'androidx.appcompat:appcompat:1.6.1'
}}
"""

SETTINGS_GRADLE = f"""pluginManagement {{
    repositories {{
        google()
        mavenCentral()
        gradlePluginPortal()
    }}
}}
dependencyResolutionManagement {{
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {{
        google()
        mavenCentral()
    }}
}}
rootProject.name = "{APP_NAME}"
include ':app'
"""

GRADLE_PROPERTIES = """org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
android.enableJetifier=true
"""

ROOT_BUILD_GRADLE = """plugins {
    id 'com.android.application' version '8.2.2' apply false
}
"""

GRADLE_WRAPPER_PROPERTIES = """distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\\://services.gradle.org/distributions/gradle-8.2-bin.zip
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
"""

NETWORK_SECURITY_CONFIG = """<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system"/>
        </trust-anchors>
    </base-config>
</network-security-config>
"""

PROGUARD_RULES = """# Add project specific ProGuard rules here.
-keep class * extends android.webkit.WebViewClient { *; }
-keep class * extends android.webkit.WebChromeClient { *; }
"""

# ── 2f. Project scaffold ─────────────────────────────────────────────────────

def generate_project(html_content: str, features: dict) -> None:
    """Write the complete Android project tree under BUILD_DIR."""
    app = BUILD_DIR / "app"
    main = app / "src" / "main"
    java_dir = main / "java" / Path(PACKAGE_PATH)
    assets_dir = main / "assets"
    res = main / "res"
    wrapper = BUILD_DIR / "gradle" / "wrapper"

    for d in [java_dir, assets_dir,
              res / "layout", res / "values", res / "xml",
              wrapper]:
        d.mkdir(parents=True, exist_ok=True)

    def write(path: Path, content: str):
        path.write_text(content, encoding="utf-8")
        log.info(f"  wrote {path.relative_to(BASE_DIR)}")

    # HTML asset
    write(assets_dir / "index.html", html_content)

    # Java source
    write(java_dir / "MainActivity.java", build_main_activity(features))

    # Manifest
    write(main / "AndroidManifest.xml", build_manifest(features))

    # Resources
    write(res / "layout" / "activity_main.xml", ACTIVITY_MAIN_XML)
    write(res / "values" / "styles.xml", STYLES_XML)
    write(res / "values" / "strings.xml", STRINGS_XML)
    write(res / "xml"    / "network_security_config.xml", NETWORK_SECURITY_CONFIG)

    # Gradle
    write(app / "build.gradle",                   APP_BUILD_GRADLE)
    write(app / "proguard-rules.pro",              PROGUARD_RULES)
    write(BUILD_DIR / "build.gradle",              ROOT_BUILD_GRADLE)
    write(BUILD_DIR / "settings.gradle",           SETTINGS_GRADLE)
    write(BUILD_DIR / "gradle.properties",         GRADLE_PROPERTIES)
    write(wrapper / "gradle-wrapper.properties",   GRADLE_WRAPPER_PROPERTIES)

    log.info("Android project generated successfully.")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SDK LOCATOR
# ═══════════════════════════════════════════════════════════════════════════════

def find_android_sdk() -> Path | None:
    """Try to locate the Android SDK root from env vars or common install paths."""
    # 1. Explicit env var
    sdk_env = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if sdk_env:
        p = Path(sdk_env)
        if p.is_dir():
            log.info(f"Android SDK found via env: {p}")
            return p

    # 2. Common install locations
    candidates = []
    if sys.platform.startswith("win"):
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk",
            Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Local" / "Android" / "Sdk",
        ]
    elif sys.platform == "darwin":
        candidates = [
            Path.home() / "Library" / "Android" / "sdk",
        ]
    else:
        candidates = [
            Path.home() / "Android" / "Sdk",
            Path("/opt/android-sdk"),
        ]

    for p in candidates:
        if p.is_dir():
            log.info(f"Android SDK found at: {p}")
            return p

    log.warning("Android SDK not found. Set ANDROID_HOME to your SDK path.")
    return None


def write_local_properties(sdk_path: Path) -> None:
    """Write local.properties so Gradle can find the SDK."""
    sdk_str = str(sdk_path).replace("\\", "\\\\")
    (BUILD_DIR / "local.properties").write_text(f"sdk.dir={sdk_str}\n")
    log.info(f"local.properties written with sdk.dir={sdk_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. APK COMPILER
# ═══════════════════════════════════════════════════════════════════════════════

def run_gradle() -> bool:
    """Execute ./gradlew assembleDebug inside the generated project."""
    gradlew = BUILD_DIR / ("gradlew.bat" if sys.platform.startswith("win") else "gradlew")

    if not gradlew.exists():
        # Download the Gradle wrapper script if not present
        log.info("gradlew not found – generating a minimal wrapper...")
        _write_gradle_wrapper_script(gradlew)

    os.chmod(gradlew, 0o755)

    cmd = [str(gradlew), "assembleDebug", "--stacktrace"]
    log.info(f"Running: {' '.join(cmd)}")
    log.info(f"Working dir: {BUILD_DIR}")

    result = subprocess.run(
        cmd,
        cwd=BUILD_DIR,
        capture_output=True,
        text=True,
    )

    log.info(result.stdout)
    if result.returncode != 0:
        log.error("Gradle build FAILED:")
        log.error(result.stderr)
        return False

    log.info("Gradle build succeeded.")
    return True


def _write_gradle_wrapper_script(gradlew: Path) -> None:
    """Write a minimal gradlew shell/bat stub that downloads and runs Gradle."""
    if sys.platform.startswith("win"):
        stub = r"""@rem Auto-generated gradlew.bat stub
@echo off
set DIRNAME=%~dp0
set APP_HOME=%DIRNAME%
set GRADLE_HOME=%USERPROFILE%\.gradle\wrapper\dists\gradle-8.2-bin
java -jar "%APP_HOME%\gradle\wrapper\gradle-wrapper.jar" %*
"""
    else:
        stub = """#!/bin/sh
# Auto-generated gradlew stub
exec java -jar "$(dirname "$0")/gradle/wrapper/gradle-wrapper.jar" "$@"
"""
    gradlew.write_text(stub)

    # Download the actual gradle-wrapper.jar
    jar_path = BUILD_DIR / "gradle" / "wrapper" / "gradle-wrapper.jar"
    if not jar_path.exists():
        try:
            import urllib.request
            url = ("https://raw.githubusercontent.com/gradle/gradle/"
                   "v8.2.1/gradle/wrapper/gradle-wrapper.jar")
            log.info(f"Downloading gradle-wrapper.jar from {url}...")
            urllib.request.urlretrieve(url, jar_path)
            log.info("gradle-wrapper.jar downloaded.")
        except Exception as e:
            log.warning(f"Could not download gradle-wrapper.jar: {e}")
            log.warning("Open build/android_project/ in Android Studio and build from there.")


def collect_apk() -> bool:
    """Copy the debug APK to output/app.apk."""
    debug_apk = (BUILD_DIR / "app" / "build" / "outputs" / "apk" /
                 "debug" / "app-debug.apk")
    if not debug_apk.exists():
        log.error(f"APK not found at expected path: {debug_apk}")
        return False

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = OUTPUT_DIR / "app.apk"
    shutil.copy2(debug_apk, dest)
    size_mb = dest.stat().st_size / 1_048_576
    log.info(f"APK saved → {dest}  ({size_mb:.2f} MB)")
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# 5. MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  HTML → APK Builder  |  Developed by BALAVIGNESH A")
    print("=" * 60)

    # ── Step 0: Check input ──────────────────────────────────────
    if not INPUT_HTML.exists():
        log.error(f"Input file not found: {INPUT_HTML}")
        log.error("Place your HTML file at:  input_project/index.html")
        sys.exit(1)

    html_content = INPUT_HTML.read_text(encoding="utf-8")
    log.info(f"Loaded {INPUT_HTML}  ({len(html_content):,} chars)")

    # ── Step 1: Analyse HTML ─────────────────────────────────────
    log.info("\n[1/4] Analysing HTML features…")
    features = analyze_html(html_content)

    # ── Step 2: Generate Android project ─────────────────────────
    log.info("\n[2/4] Generating Android project…")
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    generate_project(html_content, features)

    # ── Step 3: Locate SDK & compile ─────────────────────────────
    log.info("\n[3/4] Locating Android SDK…")
    sdk_path = find_android_sdk()

    if sdk_path is None:
        log.warning("")
        log.warning("Android SDK not found – skipping automatic APK compilation.")
        log.warning("Options:")
        log.warning("  • Set ANDROID_HOME and re-run this script, OR")
        log.warning("  • Open  build/android_project/  in Android Studio")
        log.warning("    and run Build → Generate Signed/Debug APK manually.")
        log.warning("")
        log.info(f"Build log saved → {log_filename}")
        sys.exit(0)

    write_local_properties(sdk_path)

    log.info("\n[4/4] Compiling APK with Gradle…")
    success = run_gradle()

    # ── Step 4: Collect output ────────────────────────────────────
    if success:
        collected = collect_apk()
        if collected:
            print("\n" + "=" * 60)
            print(f"  SUCCESS!  APK ready at:  output/app.apk")
            print("  Install:  adb install output/app.apk")
            print("=" * 60)
        else:
            log.error("Build succeeded but APK not found – check Gradle output.")
            sys.exit(1)
    else:
        log.error("")
        log.error("Build failed. Tips:")
        log.error("  1. Open build/android_project/ in Android Studio")
        log.error("  2. Check logs/  for the full Gradle error")
        log.error("  3. Ensure JDK 17 is installed and on your PATH")
        sys.exit(1)

    log.info(f"\nFull build log → {log_filename}")


if __name__ == "__main__":
    main()

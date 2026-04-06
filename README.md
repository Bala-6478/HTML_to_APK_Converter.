# HTML → APK Builder
**Developed by BEST_TEAM**

Convert any single-file HTML project into an installable Android APK — no Android Studio required for most tasks.

---

## 📋 Requirements

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Runs the builder |
| Java JDK | 17+ | Required by Gradle |
| Android SDK | Any recent | Compiles the APK |

> **Tip:** Install [Android Studio](https://developer.android.com/studio) — it bundles both the SDK and an easy way to build the project if the auto-compile step doesn't find your SDK.

---

## 🚀 Quick Start

1. **Place your HTML file:**
   ```
   input_project/index.html
   ```

2. **Run the builder:**
   - Windows: double-click `run_converter.bat`
   - Linux/macOS: `bash run_converter.sh`

3. **Get your APK:**
   ```
   output/app.apk
   ```

4. **Install on a device:**
   ```bash
   adb install output/app.apk
   ```

---

## ⚙️ How It Works

```
index.html
    │
    ▼
[HTML Analyser]          Detects: internet, localStorage, drag-drop,
                         iframe, file-picker, media, dark mode, geolocation
    │
    ▼
[Android Project         Generates full Gradle project with:
 Generator]              • MainActivity.java  (WebView host)
                         • AndroidManifest.xml (permissions)
                         • build.gradle, settings.gradle
                         • res/layout, res/values, res/xml
    │
    ▼
[APK Compiler]           Runs: ./gradlew assembleDebug
    │
    ▼
output/app.apk           Ready to install!
```

---

## 📁 Folder Structure

```
HTML_to_APK_Converter/
├── converter.py              ← Main Python program
├── run_converter.bat         ← Windows launcher
├── run_converter.sh          ← Linux/macOS launcher
│
├── input_project/
│   └── index.html            ← YOUR HTML FILE GOES HERE
│
├── build/
│   └── android_project/      ← Generated Android project
│       ├── app/
│       │   ├── src/main/
│       │   │   ├── assets/index.html
│       │   │   ├── java/.../MainActivity.java
│       │   │   ├── AndroidManifest.xml
│       │   │   └── res/
│       │   └── build.gradle
│       ├── settings.gradle
│       └── gradle.properties
│
├── output/
│   └── app.apk               ← Final APK (if SDK found)
│
└── logs/
    └── build_*.log           ← Detailed build logs
```

---

## 🌐 HTML Features Auto-Detected

| HTML Feature | Android Behaviour |
|---|---|
| Internal CSS | Rendered by WebView |
| Internal JavaScript | Fully enabled |
| `localStorage` / `sessionStorage` | Persists inside APK |
| External URLs (`fetch`, CDN scripts) | INTERNET permission auto-added |
| `<iframe>` | Allowed in WebView |
| Drag & Drop | WebChromeClient + FileChooser enabled |
| `<input type="file">` | Android file picker opens |
| `<video>` / `<audio>` | Autoplay enabled |
| `navigator.geolocation` | Location permission auto-added |
| `getUserMedia` | Camera + Microphone permissions auto-added |
| Dark Mode (`prefers-color-scheme`) | Follows system theme |
| `data-theme` attribute | Preserved via JS |
| WebRTC | INTERNET permission + enabled |

---

## 🔧 Customisation

Edit the top section of `converter.py`:

```python
APP_NAME     = "MyWebApp"                  # App label shown on device
PACKAGE_NAME = "com.bestteam.generatedapp" # Unique app ID
VERSION_CODE = 1
VERSION_NAME = "1.0"
MIN_SDK      = 21                          # Android 5.0+
TARGET_SDK   = 34                          # Android 14
```

---

## 🛠 Troubleshooting

**"Android SDK not found"**
→ Install Android Studio, then set the environment variable:
```bash
# Windows
set ANDROID_HOME=C:\Users\YOU\AppData\Local\Android\Sdk

# Linux/macOS
export ANDROID_HOME=$HOME/Android/Sdk
```

**"Java not found"**
→ Install JDK 17+ and ensure `java` is on your PATH.

**Build fails with Gradle error**
→ Open `build/android_project/` in Android Studio and build from there.

**APK installs but HTML doesn't load**
→ Ensure your `index.html` uses **relative paths only** — no absolute `file://` paths.

---

## 📦 Output APK Behaviour

- Opens directly to your HTML page (no browser chrome)
- Back button navigates web history, then exits
- All JS, CSS, `localStorage` work identically to the browser
- Permissions are requested automatically based on HTML features

---

*Developed by BEST_TEAM — HTML → APK Builder*

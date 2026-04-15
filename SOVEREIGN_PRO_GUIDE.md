# Sovereign Agent: Professional Deployment Guide

The Sovereign Agent has been transformed from a developer script into a **Standard Windows Professional Software**. All data is now persistent, and all settings are managed directly through the GUI.

---

## 🚀 The 3-Step Build Process (Explained)

To create the final, professional installer (`Setup.exe`), you need to follow these two technical stages:

### Step 1: Build the Software Engine
Run this command in your terminal:
```bash
python build.py
```
**What this does**: It uses `PyInstaller` to take all your Python code and bundle it into a professional **Program Folder** inside `dist/SovereignAgent`. It strips out unnecessary libraries (like big data science modules) to make the app much smaller and professional.

### Step 2: Compile the Professional Installer
1. Install [Inno Setup](https://jrsoftware.org/isdl.php) (the industry standard for Windows installers).
2. Open the file **`SovereignInstaller.iss`** (located in your project root) using Inno Setup.
3. Click the **"Compile"** button (looks like a play icon).
**What this does**: It takes the folder from Step 1 and packages it into a single, branded **`Sovereign_Agent_Setup_v25.exe`**.

### Step 3: Deploy
You now have a professional installer that:
- Installs the app into `C:\Program Files\Sovereign Agent`.
- Creates a Start Menu shortcut.
- Does **not** lose data when you close it (saves to `AppData`).

---

## 🛠️ Key Architecture Changes

### 1. Perpetual Memory (Persistence)
- **Data Location**: `%APPDATA%\TDWAS\SovereignAgent`.
- **Why?**: Standard Windows apps store data here so it's never lost during updates or reboots.

### 2. Mandatory Mission Briefing (The Lock)
- **Change**: The app is now **Locked** until the user completes the 4-step wizard.
- **Requirement**: You must set your AI Keys, Profile, and Upload a Resume before the Dashboard becomes active. This ensures the agent is "Mission-Ready."

### 3. Identity Sovereign Hub
- **Access**: Click **📋 ASSET HUB** in the sidebar.
- **Features**: 
    - **Upload PDF/DOCX**: Direct buttons to link your master resumes.
    - **Identity Editor**: A full form to edit your name, experience, and history without touching code files.

---

> [!IMPORTANT]
> **Anti-Malware**: Because the app installs to `Program Files` and has proper TDWAS Technology metadata, it is much more trusted by Windows Security than a standalone EXE.

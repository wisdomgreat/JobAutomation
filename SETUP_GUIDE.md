# 🖥️ Sovereign Agent: Multi-Platform Setup Guide

Welcome to the comprehensive setup guide for Sovereign Agent. Whether you are running on Windows, macOS, or Linux, this guide will walk you through deploying your personal automation engine.

---

## 🟦 Windows Setup

Windows users have two options: a simple, no-install Portable Executable or running directly from the source code.

### Option A: The Portable Executable (Recommended)
This is the easiest way to launch Sovereign Agent on Windows without needing technical knowledge or installing Python.

1. Navigate to the [Releases Page](https://github.com/wisdomgreat/JobAutomation/releases/latest).
2. Download the latest `SovereignAgent_Portable_vX.X.X.zip`.
3. Extract the `.zip` file into a dedicated folder (e.g., `C:\SovereignAgent`).
4. **Double-click** `SovereignAgent_Portable.exe` to launch.
   > **Note:** Windows Defender SmartScreen may block the execution. To bypass, click **"More info"** and then **"Run anyway"**.

### Option B: Running from Source
If you are a developer or prefer running natively through the terminal.

1. **Install Git**: Download from [git-scm.com](https://git-scm.com/downloads) and install.
2. **Install Python**: Download Python 3.10+ from [Python.org](https://www.python.org/downloads/). During installation, **you MUST check the box that says "Add Python to PATH."**
3. Open **Command Prompt** or **PowerShell** and run:
   ```cmd
   git clone https://github.com/wisdomgreat/JobAutomation
   cd JobAutomation
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python gui.py
   ```

---

## 🍏 macOS Setup

macOS requires running the agent directly from the source code. You will use the Terminal application (accessible via Spotlight).

### 1. Pre-requisites
macOS comes with Python out of the box, but often it's an outdated version. We highly recommend installing the latest version.
* Install Homebrew (if you don't have it):
  ```bash
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```
* Install Git and Python 3:
  ```bash
  brew install git python3
  ```

### 2. Setup and Launch
Open your Terminal and run the following commands sequentially:
```bash
# Clone the repository to your local machine
git clone https://github.com/wisdomgreat/JobAutomation

# Navigate into the project folder
cd JobAutomation

# Create an isolated virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install the required software packages
pip3 install -r requirements.txt

# Launch Sovereign Agent Mission Control
python3 gui.py
```
> **Tip:** You may need to grant Terminal permission to control the browser in your macOS Privacy & Security settings if it is tracking web elements.

---

## 🐧 Linux & Unix Setup

Linux environments require running from source. These instructions are tailored for Debian/Ubuntu-based distributions but apply generally to any Linux architecture with standard package managers.

### 1. Pre-requisites
Launch your terminal and ensure your system dependencies are up-to-date:
```bash
sudo apt update
sudo apt install git python3 python3-pip python3-venv xvfb
```
> *Note on `xvfb`: This allows the browser instances to run efficiently, or in headless states if you plan on deploying Sovereign Agent to a remote/cloud Unix server.*

### 2. Setup and Launch
```bash
# Clone the repository
git clone https://github.com/wisdomgreat/JobAutomation
cd JobAutomation

# Create and activate the virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the required dependencies
pip install -r requirements.txt

# Boot up the Sovereign GUI
python3 gui.py
```

---

## 🛠️ Global Troubleshooting

> [!WARNING]
> If you encounter issues while setting up, here are the most common solutions:

1. **`python` or `pip` is not recognized**
   * **Windows**: Re-run the Python installer and ensure "Add Python to PATH" is checked.
   * **Linux/Mac**: Use `python3` and `pip3` instead of `python` and `pip`.

2. **Browser Fails to Launch / Drivers Not Found**
   * Sovereign Agent relies on having an up-to-date modern browser installed locally. Ensure you have the latest stable version of Google Chrome or Microsoft Edge installed on your system.

3. **Dependency Conflict Errors (`pip install` fails)**
   * This mostly happens on Linux. Fix this by ensuring you are inside the virtual environment (`source venv/bin/activate`).
   * If you're encountering permission errors, try installing wheel first: `pip install wheel`.

4. **"Application has been destroyed" (Windows)**
   * This is a known Python 3.13 Tkinter UI rendering issue that is patched dynamically. Ensure you update your repository via `git pull` if running from source to receive the latest Window Management optimizations.

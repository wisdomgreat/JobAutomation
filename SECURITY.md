# Security Policy

## Supported Versions

TDWAS Sovereign Agent is an intelligence-driven professional software. We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 26.x    | :white_check_mark: |
| 25.x    | :x:                |
| < 25.0  | :x:                |

## 🛡️ Security False Positives
The Sovereign Agent is an automation tool that uses browser drivers and network requests. Because the binaries are currently **unsigned**, Windows SmartScreen and Antivirus software (like Avast or Windows Defender) may flag the application as "unrecognized" or "suspicious."

### How to Bypass SmartScreen
1. When the blue "Windows protected your PC" window appears, click **"More info"**.
2. Click the **"Run anyway"** button that appears.

### How to Bypass Antivirus (Avast/Defender)
1. If Avast flags the file as suspicious, you can add an **Exclusion** to the folder where you installed the agent.
2. In Avast: Menu > Settings > Exceptions > Add Exception.
3. Browse to the installation directory (usually `C:\Program Files\Sovereign Agent`).

## 📜 Code Signing Certificate
To fully eliminate these warnings, the binaries must be signed with a Code Signing Certificate from a trusted Certificate Authority (CA).

### How to obtain a Certificate:
1. **Choose a CA**: Common providers include **Sectigo**, **DigiCert**, and **GlobalSign**.
2. **Select Type**: 
   - **OV (Organization Validation)**: Standard, cheaper, requires business verification.
   - **EV (Extended Validation)**: More expensive, requires strict verification, but gives instant reputation with SmartScreen.
3. **Hardware Requirement**: As of 2023, most CAs require a **Yubikey** or Cloud HSM to store the certificate keys.
4. **Verification**: You will need to provide business registration or legal identity documents.

Once a certificate is obtained, the build process can be updated to automatically sign the EXE files using `signtool.exe`.

## Reporting a Vulnerability

**Do not report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability within the Sovereign Agent ecosystem, please report it privately via one of the following channels:

- **Email**: security@tdwas.com (Response within 24-48 hours)
- **Private Disclosure**: Use the GitHub "Report a vulnerability" feature in the Security tab.

We appreciate your help in keeping the Sovereign Agent secure for all professional users.

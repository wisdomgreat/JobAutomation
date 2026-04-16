import re
import argparse
from pathlib import Path

def bump_version(current_version, bump_type):
    major, minor, patch = map(int, current_version.split('.'))
    
    if bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    else:
        patch += 1
        
    return f"{major}.{minor}.{patch}"

def update_version_file(version_path, new_version):
    version_path.write_text(new_version)
    print(f"[VERSION] Updated to {new_version}")

def update_iss_file(iss_path, new_version):
    content = iss_path.read_text()
    # Matches: #define MyAppVersion "X.Y" or "X.Y.Z"
    new_content = re.sub(r'(#define MyAppVersion\s+)"[^"]+"', rf'\g<1>"{new_version}"', content)
    # Also update OutputBaseFilename to keep it consistent
    base_version = '.'.join(new_version.split('.')[:2]) # 26.6
    new_content = re.sub(r'(OutputBaseFilename=Sovereign_Agent_Setup_v)\d+', rf'\g<1>{new_version.replace(".", "_")}', new_content)
    
    iss_path.write_text(new_content)
    print(f"[ISS] Updated {iss_path.name}")

def update_version_info(info_path, new_version):
    content = info_path.read_text()
    major, minor, patch = map(int, new_version.split('.'))
    
    # Update tuple formats
    content = re.sub(r'(filevers=\()[\d,\s]+(\))', rf'\g<1>{major}, {minor}, {patch}, 0\g<2>', content)
    content = re.sub(r'(prodvers=\()[\d,\s]+(\))', rf'\g<1>{major}, {minor}, {patch}, 0\g<2>', content)
    
    # Update string structs
    content = re.sub(r"(StringStruct\(u'FileVersion',\s+u')[^']+(\'\))", rf"\g<1>{new_version}\g<2>", content)
    content = re.sub(r"(StringStruct\(u'ProductVersion',\s+u')[^']+(\'\))", rf"\g<1>{new_version}\g<2>", content)
    
    info_path.write_text(content)
    print(f"[TXT] Updated {info_path.name}")

def main():
    parser = argparse.ArgumentParser(description='Sovereign Agent Version Bumper')
    parser.add_argument('--type', choices=['patch', 'minor', 'major'], default='patch')
    args = parser.parse_args()
    
    root = Path(__file__).parent.parent.parent
    version_path = root / "VERSION"
    iss_path = root / "SovereignInstaller.iss"
    info_path = root / "file_version_info.txt"
    
    if not version_path.exists():
        print("❌ VERSION file not found!")
        return

    current_version = version_path.read_text().strip()
    new_version = bump_version(current_version, args.type)
    
    update_version_file(version_path, new_version)
    if iss_path.exists(): update_iss_file(iss_path, new_version)
    if info_path.exists(): update_version_info(info_path, new_version)
    
    print(f"\nSuccessfully bumped version: {current_version} -> {new_version}")

if __name__ == "__main__":
    main()

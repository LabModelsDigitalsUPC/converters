#!/usr/bin/env python3
"""
Build executables for IFC-to-RDF-Geom converter offline
This script creates PyInstaller executables for the current platform
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def get_repo_root():
    """Get repository root path relative to script location"""
    script_dir = Path(__file__).parent
    # Go up 2 levels from IFC-converters/IFC-to-RDF-Geom to reach repo root
    repo_root = script_dir.parent.parent
    return repo_root

def get_platform_info():
    """Get platform-specific information"""
    system = platform.system().lower()
    
    if system == "windows":
        return {
            "name": "windows",
            "executable_ext": ".exe",
            "separator": ";"
        }
    elif system == "darwin":
        return {
            "name": "macos", 
            "executable_ext": "",
            "separator": ":"
        }
    elif system == "linux":
        return {
            "name": "linux",
            "executable_ext": "",
            "separator": ":"
        }
    else:
        raise ValueError(f"Unsupported platform: {system}")

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        ("PyInstaller", "pyinstaller"),  # (import_name, pip_name)
        ("ifcopenshell", "ifcopenshell"), 
        ("rdflib", "rdflib"),
        ("numpy", "numpy"),
        ("pygltflib", "pygltflib")
    ]
    
    print("Checking dependencies...")
    missing_packages = []
    
    for import_name, pip_name in required_packages:
        try:
            if import_name == "PyInstaller":
                # Special case for PyInstaller
                import PyInstaller
            else:
                __import__(import_name)
            print(f"[OK] {pip_name}")
        except ImportError:
            missing_packages.append(pip_name)
            print(f"[MISSING] {pip_name}")
    
    if missing_packages:
        print("\nMissing packages found. Install them with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("All dependencies are installed!")
    return True

def build_executable(source_dir, platform_info):
    """Build the executable using PyInstaller"""
    
    # Define paths
    script_path = Path(source_dir) / "compact_ifc_converter.py"
    conversion_map_path = Path(source_dir) / "conversion-map.json"
    
    # Verify files exist
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")
    if not conversion_map_path.exists():
        raise FileNotFoundError(f"Conversion map not found: {conversion_map_path}")
    
    # Get repository root based on script location
    repo_root = get_repo_root()
    
    print(f"Repository root: {repo_root}")
    print(f"Script directory: {Path(__file__).parent}")
    
    # Build PyInstaller command with custom dist directory
    dist_dir = repo_root / "dist"
    cmd = [
        sys.executable,  # Use the current Python interpreter
        "-m",
        "PyInstaller",
        "--onefile",
        "--distpath", str(dist_dir),
        "--workpath", str(repo_root / "build"),
        "--specpath", str(repo_root),
        "--add-data", f"{conversion_map_path}{platform_info['separator']}IFC-to-RDF-Geom",
        str(script_path)
    ]
    
    print(f"Building executable for {platform_info['name']}...")
    print(f"Command: {' '.join(cmd)}")
    print(f"Dist directory will be: {dist_dir}")
    
    # Run PyInstaller
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    
    if result.returncode != 0:
        print("PyInstaller failed!")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        return False
    
    print("PyInstaller completed successfully!")
    return True

def organize_output(platform_info):
    """Organize the output files"""
    
    # Get repository root based on script location
    repo_root = get_repo_root()
    
    # Create platform-specific directory
    platform_dir = repo_root / "dist" / platform_info["name"]
    platform_dir.mkdir(parents=True, exist_ok=True)
    
    # Source and destination paths
    source_exe = repo_root / "dist" / f"compact_ifc_converter{platform_info['executable_ext']}"
    dest_exe = platform_dir / f"ifc-to-rdf-geom{platform_info['executable_ext']}"
    
    # Move the executable
    if source_exe.exists():
        if dest_exe.exists():
            dest_exe.unlink()  # Remove existing file
        shutil.move(str(source_exe), str(dest_exe))
        print(f"Executable moved to: {dest_exe}")
        
        # Make executable on Unix-like systems
        if platform_info["name"] in ["linux", "macos"]:
            os.chmod(dest_exe, 0o755)
            print("Made executable")
        
        return dest_exe
    else:
        print(f"Error: Expected executable not found at {source_exe}")
        return None

def clean_build_files():
    """Clean up build artifacts"""
    
    # Get repository root based on script location
    repo_root = get_repo_root()
    
    build_dir = repo_root / "build"
    spec_file = repo_root / "compact_ifc_converter.spec"
    
    # Clean build directory with retry logic
    if build_dir.exists():
        max_retries = 3
        for attempt in range(max_retries):
            try:
                shutil.rmtree(build_dir)
                print("Cleaned build directory")
                break
            except PermissionError as e:
                if attempt < max_retries - 1:
                    print(f"Permission error cleaning build directory (attempt {attempt + 1}/{max_retries}). Retrying...")
                    import time
                    time.sleep(2)  # Wait 2 seconds before retry
                else:
                    print(f"Warning: Could not clean build directory: {e}")
                    print("You may need to manually delete:", build_dir)
    
    # Clean spec file
    if spec_file.exists():
        try:
            spec_file.unlink()
            print("Cleaned spec file")
        except PermissionError as e:
            print(f"Warning: Could not clean spec file: {e}")
            print("You may need to manually delete:", spec_file)

def main():
    """Main build process"""
    print("IFC-to-RDF-Geom Executable Builder")
    print("=" * 40)
    
    # Check for --all-platforms flag
    if "--all-platforms" in sys.argv:
        print("\nThis script builds for the CURRENT platform only.")
        print(f"Current platform: {platform.system()}")
        print("\nTo build for all platforms, you need to:")
        print("1. Run this script on each target OS, OR")
        print("2. Use GitHub Actions (recommended), OR")
        print("3. Use Docker for Linux builds")
        print("\nRun 'python generate_multi_platform_build.py' to set up GitHub Actions.")
        sys.exit(0)
    
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)
    
    # Get platform information
    try:
        platform_info = get_platform_info()
        print(f"Building for platform: {platform_info['name']}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Default source directory - same directory as this script
    default_source_dir = Path(__file__).parent
    
    # Allow custom source directory via command line
    if len(sys.argv) > 1:
        source_dir = Path(sys.argv[1])
    else:
        source_dir = default_source_dir
    
    print(f"Source directory: {source_dir}")
    
    # Verify source directory exists
    if not source_dir.exists():
        print(f"Error: Source directory not found: {source_dir}")
        print("Usage: python build_executables.py [source_directory]")
        sys.exit(1)
    
    try:
        # Build executable
        if not build_executable(source_dir, platform_info):
            sys.exit(1)
        
        # Organize output
        output_path = organize_output(platform_info)
        if not output_path:
            sys.exit(1)
        
        # Clean up
        try:
            clean_build_files()
        except Exception as e:
            print(f"Warning during cleanup: {e}")
            print("Build artifacts may need manual cleanup, but executable was created successfully.")
        
        print("\n" + "=" * 40)
        print("BUILD SUCCESSFUL!")
        print(f"Executable created at: {output_path}")
        print(f"File size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
        
        # Test the executable
        print("\nTesting executable...")
        try:
            test_result = subprocess.run([str(output_path), "--help"], 
                                       capture_output=True, text=True, timeout=10)
            
            if test_result.returncode == 0:
                print("[OK] Executable runs successfully!")
            else:
                print("[WARNING] Executable may have issues:")
                print(test_result.stderr)
        except subprocess.TimeoutExpired:
            print("[WARNING] Executable test timed out")
        except Exception as e:
            print(f"[WARNING] Could not test executable: {e}")
        
    except KeyboardInterrupt:
        print("\nBuild interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error during build: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
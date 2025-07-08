# Compact IFC Converter

---

## 📑 Index
1. [Overview](#overview)
2. [User Guide](#user-guide)
    - [Requirements](#requirements)
    - [How to Use the Executable](#how-to-use-the-executable)
    - [Command Line Usage](#command-line-usage)
    - [Examples](#examples)
    - [Output](#output)
3. [Developer Guide](#developer-guide)
    - [Project Structure](#project-structure)
    - [Code Overview](#code-overview)
    - [Development & Contribution](#development--contribution)
    - [Automated Build Pipeline](#automated-build-pipeline)
4. [Notes](#notes)

---

## 🏗️ Overview

**IFC to RDF + Geometry Converter** is a tool to convert IFC files to RDF metadata and GLB geometry. It is self-contained, configurable, and can be used as a command-line tool or as a standalone executable (no Python required for users of the executable).

---

## 👤 User Guide

### Requirements

- **If using the Python script:**
  - Python 3.7+
  - Required Python packages:
    - ifcopenshell
    - rdflib
    - numpy
    - pygltflib

  Install dependencies with:
  ```sh
  pip install ifcopenshell rdflib numpy pygltflib
  ```

- **If using the executable:**
  - No Python installation required!
  - Download the appropriate executable for your OS from the [GitHub Actions Artifacts](../../actions) after a successful build.

### How to Use the Executable

1. **Download** the executable for your platform (Windows, Linux, or macOS) from the GitHub Actions run artifacts.
2. **Place** your IFC file in a convenient directory.
3. **Open a terminal** (Command Prompt, PowerShell, or Terminal) in the directory containing the executable.
4. **Run the converter:**
   ```sh
   # Windows example
   .\compact_ifc_converter.exe my_model.ifc

   # Linux/macOS example
   ./compact_ifc_converter my_model.ifc
   ```
5. **Optional:** Use command-line arguments for custom output, see below.

### Command Line Usage

```sh
python IFC-to-RDF-Geom/compact_ifc_converter.py <path_to_ifc_file> [options]
# OR (if using the executable)
./compact_ifc_converter <path_to_ifc_file> [options]
```

#### Command Line Arguments

| Argument                | Description                                                      | Default                        |
|-------------------------|------------------------------------------------------------------|--------------------------------|
| `<ifc_file>`            | Path to the IFC file to convert                                  | (required)                     |
| `--asset-name`, `-n`    | Name for output files (without extension)                        | IFC filename (without ext)     |
| `--base-url`, `-u`      | Base URL for RDF namespaces                                      | http://localhost:8000/data/    |
| `--rdf-output`, `-r`    | Output directory for RDF files                                   | ./data/rdf                     |
| `--glb-output`, `-g`    | Output directory for GLB files                                   | ./data/glb                     |
| `--no-geometry`         | Skip GLB geometry conversion (RDF only)                          | (geometry is converted by default) |
| `--conversion-map`, `-m`| Path to a custom conversion map JSON file                        | conversion-map.json (default)  |
| `--verbose`, `-v`       | Enable verbose logging                                           | (off by default)               |

### Examples

Convert an IFC file and output RDF and GLB:
```sh
./compact_ifc_converter my_model.ifc
```

Specify a custom asset name and output directories:
```sh
./compact_ifc_converter my_model.ifc -n MyAsset -r ./rdf_out -g ./glb_out
```

Convert only to RDF (skip geometry):
```sh
./compact_ifc_converter my_model.ifc --no-geometry
```

Use a custom conversion map:
```sh
./compact_ifc_converter my_model.ifc -m ./my_conversion_map.json
```

Enable verbose logging for debugging:
```sh
./compact_ifc_converter my_model.ifc --verbose
```

### Output
- RDF file: `<asset_name>.ttl` in the RDF output directory
- GLB file: `<asset_name>.glb` in the GLB output directory (unless `--no-geometry` is used)

---

## 👩‍💻 Developer Guide

### Project Structure
```
IFC-converters/
  └─ IFC-to-RDF-Geom/
      ├─ compact_ifc_converter.py   # Main converter script
      ├─ conversion-map.json       # Mapping configuration for RDF conversion
      └─ README.md                 # This documentation
```

### Code Overview
- **compact_ifc_converter.py**
  - Contains the `CompactIFCConverter` class, which:
    - Loads and parses IFC files
    - Converts geometry to GLB (using pygltflib)
    - Extracts and maps metadata to RDF (using rdflib)
    - Uses a configurable `conversion-map.json` for flexible mapping
    - Handles both command-line and programmatic usage
  - Includes a `resource_path` utility for PyInstaller compatibility
  - Has a CLI interface for direct use
- **conversion-map.json**
  - Defines how IFC classes and properties are mapped to RDF/OWL ontologies
  - Can be customized or replaced for different mapping needs

### Development & Contribution
- Clone the repository and install dependencies (see [Requirements](#requirements)).
- Make changes in a feature branch.
- Ensure code is clean and well-documented.
- Test locally with various IFC files.
- Pull requests are welcome!

### Automated Build Pipeline
- GitHub Actions workflow automatically builds executables for Windows, Linux, and macOS on every push/PR to the converter folder.
- Artifacts are uploaded for easy download and testing.
- The workflow uses PyInstaller and bundles `conversion-map.json` for standalone use.

---

## 📝 Notes
- The script and executables will create output directories if they do not exist.
- The conversion map (`conversion-map.json`) should be in the same directory as the script/executable unless a custom path is provided.
- For advanced mapping, edit or replace `conversion-map.json`.
- For issues or feature requests, please open an issue on GitHub.

---

✨ **Happy converting!** ✨
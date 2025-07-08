# Data Converters Repository

---

## 📦 Purpose

This repository is dedicated to hosting a collection of **data converters** designed for various purposes, such as transforming files between formats, extracting metadata, or integrating with different platforms and ontologies. The aim is to provide a centralized, well-organized, and easy-to-extend set of tools for users and developers across different domains.

---

## 🗂️ Folder Organization

- Each converter is placed in its **own thematic subfolder** under the repository root (e.g., `IFC-converters/` is for converters dedicated to IFC data).
- Each converter folder contains:
  - The main converter script(s)
  - Configuration or mapping files
  - Documentation (`README.md`)
  - Any additional resources required by the converter
- The `dist/` folder (at the repository root) contains the **built executables** for each converter, making it easy to find and use the compiled tools without needing to build from source.

**Example structure:**
```
repo-root/
  ├─ IFC-converters/
  │    ├─ IFC-to-RDF+Geom/
  │    │    ├─ compact_ifc_converter.py
  │    │    ├─ conversion-map.json
  │    │    └─ README.md
  │    └─ ...
  ├─ dist/
  │    ├─ IFC-to-RDF+Geom.exe
  │    └─ ...
  └─ README.md  # (this file)
```

---

## 🚀 Getting Started

1. Browse the converter folders to find the tool that fits your needs.
2. Download the corresponding executable from the `dist/` folder.
3. Refer to each converter's `README.md` for usage instructions and requirements.

---

## 🤝 Contributing

- To add a new converter, create a new subfolder and follow the structure above.
- Document your converter thoroughly to help users and future contributors.
- Submit a pull request with your changes for review.

---

**Let's build a robust and user-friendly ecosystem of data converters together!** 

---

## 📥 How to Download Executables from GitHub Actions

If you do not see the executables in the `dist/` folder, you can download the latest built versions directly from GitHub Actions as follows:

1. Go to the [Actions](../../actions) tab of this repository on GitHub.
2. Click on the most recent workflow run for the converter you are interested in (e.g., 'Build ifc-to-rdf+geom executables').
3. Scroll to the bottom of the workflow run summary page.
4. Under the 'Artifacts' section, click the name of the artifact (e.g., `ifc-to-rdf+geom-windows`, `ifc-to-rdf+geom-linux`, or `ifc-to-rdf+geom-macos`) to download the executable for your platform.
5. Unzip the downloaded file if necessary and follow the usage instructions in the converter's `README.md`.

If you need a permanent or public download link, please contact the maintainers or check the Releases tab for official releases. 
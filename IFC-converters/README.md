# IFC Converters Repository

---

## 📚 Overview

This repository is dedicated to hosting a collection of **converters** that utilize IFC (Industry Foundation Classes) data for various purposes, such as transforming IFC files into other formats, extracting metadata, or integrating with different platforms and ontologies.

The goal is to provide a **homogeneous, well-documented, and easy-to-extend** set of tools for the AEC (Architecture, Engineering, and Construction) and related industries.

---

## 🗂️ Repository Organization

- Each converter is placed in its **own subfolder** under the repository root.
- Each converter folder contains:
  - The main converter script(s)
  - A dedicated `README.md` with user and developer documentation
  - Any configuration or mapping files (e.g., `conversion-map.json`)
  - A GitHub Actions workflow (in `.github/workflows/`) for automated builds and artifact generation

**Example structure:**
```
IFC-converters/
  ├─ IFC-to-RDF+Geom/
  │    ├─ compact_ifc_converter.py
  │    ├─ conversion-map.json
  │    └─ README.md
  ├─ Another-Converter/
  │    ├─ another_converter.py
  │    └─ README.md
  └─ README.md  # (this file)
.github/
  └─ workflows/
      ├─ build-IFC-to-RDF+Geom.yml
      └─ build-Another-Converter.yml
```

---

## 🚦 Standard Process for Adding a New Converter

To ensure consistency and maintainability, **follow these steps when adding a new converter:**

### 1. Create a New Folder
- Place all code, configuration, and documentation for your converter in a dedicated subfolder (e.g., `IFC-to-XYZ/`).

### 2. Write a Well-Structured README
- Include an index/table of contents.
- Provide a clear user guide (requirements, usage, examples, output).
- Provide a developer guide (project structure, code overview, contribution guidelines, build pipeline).
- Use section headers, tables, and examples for clarity.
- See the `IFC-to-RDF+Geom/README.md` for a template.

### 3. Annotate and Document Your Code
- Use docstrings for all classes and functions.
- Add inline comments for complex logic.
- Ensure variable and function names are descriptive.
- Make the code easy to follow for future contributors.

### 4. Add a GitHub Actions Workflow
- Create a workflow YAML file in `.github/workflows/` (e.g., `build-IFC-to-XYZ.yml`).
- The workflow should:
  - Build the converter for all major platforms (Windows, Linux, macOS) using PyInstaller or a suitable tool.
  - Bundle any required data/config files.
  - Upload the resulting executables as artifacts.
  - Trigger only on changes to the converter's folder or its workflow file (use the `paths` filter).
- See `build-IFC-to-RDF+Geom.yml` for an example.

### 5. Test Everything
- Ensure the converter works as expected locally and as a built executable.
- Check that the workflow completes successfully and artifacts are downloadable.
- Update the README with any new findings or requirements.

### 6. Keep it Homogeneous
- Follow the same structure, naming conventions, and documentation style as existing converters.
- Use markdown best practices for readability.
- Encourage contributions and improvements via pull requests.

---

## 📝 Best Practices
- **Documentation first:** Make it easy for users and developers to understand and use your converter.
- **Automation:** Use CI/CD for builds and artifact delivery.
- **Modularity:** Keep each converter self-contained.
- **Reusability:** Where possible, share utility scripts or patterns across converters.
- **Openness:** Welcome issues, suggestions, and contributions.

---

## 🤝 Contributing
- Fork the repository and create a feature branch for your converter or improvement.
- Follow the process above for new converters.
- Open a pull request with a clear description of your changes.
- Review and feedback are encouraged to maintain quality and consistency.

---

## ✨ Example: Adding a New Converter
1. Create `IFC-to-XYZ/` and add your code and `README.md`.
2. Annotate your code and document all features and usage.
3. Add a workflow file: `.github/workflows/build-IFC-to-XYZ.yml`.
4. Push your branch and check the Actions tab for build results.
5. Download and test the executable artifact.
6. Submit your pull request!

---

**Let’s build a robust, user-friendly, and extensible ecosystem of IFC converters to get our lab growing healthy!** 
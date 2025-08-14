# Integrating MkDocs for Public Documentation

This guide provides a step-by-step plan for integrating a professional, searchable documentation site into the ecosystem using MkDocs. This represents the **public-facing layer** of our three-part documentation strategy.

## Documentation Strategy Recap

1.  **Source of Truth (/.md/ & Code Docstrings):** Internal, collaborative Markdown files and the docstrings within the Python source code. **This is where we write.**
2.  **Agent Ingestion (/.ingest/):** Compiled, token-efficient JSON files for agents, generated from both Markdown and docstrings. **This is what agents read.**
3.  **Public Docs (/docs/):** Curated, polished content for end-users, built by MkDocs from both Markdown and docstrings. **This is what the world sees.**

## Step 1: Add Dependencies

Add MkDocs, the Material theme, and the mkdocstrings plugin to requirements.txt.

```text

# Documentation

mkdocs
mkdocs-material
mkdocstrings\[python\]

```

## Step 2: Configure mkdocs.yml

Update your mkdocs.yml file to enable and configure the mkdocstrings plugin.

```yaml
# mkdocs.yml
site_name: DevEnviro Ecosystem Documentation
site_url: [https://docs.devenviro.as/](https://docs.devenviro.as/)
repo_url: [https://github.com/ApexSigma-Solutions/devenviro.as](https://github.com/ApexSigma-Solutions/devenviro.as)

theme:
  name: material
  palette:
    - scheme: default
      toggle:
        icon: material/weather-sunny
        name: Switch to dark mode
    - scheme: slate
      toggle:
        icon: material/weather-night
        name: Switch to light mode
  features:
    - navigation.tabs
    - search.suggest
    - content.code.copy

# Add the mkdocstrings plugin
plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          options:
            show_source: true

# The 'nav' section defines the site's navigation.
nav:
  - 'Introduction': 'index.md'
  - 'Tutorials': 'tutorials/index.md'
  - 'How-To Guides': 'how-to/index.md'
  - 'API Reference':
    - 'reference/index.md'
    - 'Services': 'reference/services.md'

```

## Step 3: Automate API Doc Generation

Instead of manually creating API documentation, we will let mkdocstrings generate it automatically.

1.  **Create a Reference Markdown File:** In your `/docs` directory, create a file named `reference/services.md`.

2.  **Add the Docstring Directive:** Inside this file, add a single line that tells mkdocstrings which Python module to scan. The `:::` syntax will automatically pull in all functions and classes from that file and render their docstrings.
    
    ```text
    # /docs/reference/services.md
    
    ::: app.main
    
    ```

## Step 4: The Unified Build Process

Our `build_docs.py` script now has two primary responsibilities: copying our handwritten Markdown and letting mkdocstrings handle the code.

**The script's responsibilities:**

1.  **Clean:** Delete the contents of the `/docs` directory (except for files with mkdocstrings directives) to ensure a fresh build.
2.  **Select & Copy:** Read the `/.md/` directory and copy the approved, public-facing documents into the `/docs` directory.
3.  **Trigger MkDocs:** The `mkdocs serve` or `mkdocs build` command will now automatically find the `::: app.main` directive and generate the API documentation on the fly.

## Step 5: Run the Local Docs Server

1.  **Run the build script** to populate the `/docs` directory with your handwritten guides.
2.  **Serve the site** using MkDocs.
    ``` bash
    mkdocs serve
    
    ```
3.  **View the site** at `http://127.0.0.1:8000`. Navigate to the "API Reference" section to see your auto-generated documentation from your Python docstrings.

<!-- end list -->

import tomllib  # Python 3.11+
from pathlib import Path
import sys

def main():
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        print("pyproject.toml not found", file=sys.stderr)
        sys.exit(1)

    with open(pyproject, "rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    tool_setuptools = data.get("tool", {}).get("setuptools", {})
    dependencies = project.get("dependencies", [])
    optional_deps = data.get("project", {}).get("optional-dependencies", {})

    dist_name = project.get("name")
    version = project.get("version")
    description = project.get("description", "")
    
    # Extract author information
    authors = project.get("authors", [])
    if authors and isinstance(authors[0], dict):
        author = authors[0].get("name", "")
        author_email = authors[0].get("email", "")
    elif authors and isinstance(authors[0], str):
        # Handle case where authors is a list of strings like ["Name <email>"]
        author_parts = authors[0].split("<")
        author = author_parts[0].strip()
        author_email = author_parts[1].rstrip(">").strip() if len(author_parts) > 1 else ""
    else:
        author = ""
        author_email = ""
    
    # Extract license
    license_info = project.get("license", {})
    if isinstance(license_info, dict):
        license_name = license_info.get("text", "")
    else:
        license_name = str(license_info)
    
    # Extract URLs
    urls = project.get("urls", {})
    homepage = urls.get("Homepage", "https://github.com/chobie/mimicel")
    
    requires_python = project.get("requires-python", "")
    classifiers = project.get("classifiers", [])
    requires = [f'"{dep}"' for dep in dependencies]
    dev_requires = optional_deps.get("dev", [])

    print(f"""py_wheel(
    name = "{dist_name}_wheel",
    distribution = "{dist_name}",
    version = "{version}",
    python_tag = "py3",
    platform = "any",
    homepage = "{homepage}",
    summary = "{description}",
    author = "{author}",
    author_email = "{author_email}",
    license = "{license_name}",
    python_requires = "{requires_python}",
    requires = [{', '.join(requires)}],
    extra_requires = {{
        "dev": [{', '.join(f'"{d}"' for d in dev_requires)}],
    }},
    description_file = "//:README.md",
    description_content_type = "text/markdown",
    extra_distinfo_files = {{
        "//:LICENSE": "LICENSE",
    }},
    deps = [
        ":{dist_name}_pkg",
    ],
)""")

if __name__ == "__main__":
    main()
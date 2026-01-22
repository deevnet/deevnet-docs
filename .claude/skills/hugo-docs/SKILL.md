---
name: hugo-docs
description: Validate and build Hugo documentation. Use after editing markdown files in content/ to verify syntax and catch build errors.
argument-hint: "[--build]"
---

# Hugo Documentation Validation

When invoked, validate Hugo documentation by running the build process.

## Validation Steps

1. **Run Hugo build with minification** to catch syntax errors and validate all content:
   ```bash
   cd /srv/dvnt/deevnet-docs && hugo --minify --destination /tmp/hugo-build-check
   ```

2. **Check the output** for:
   - Build errors (template issues, broken shortcodes)
   - Warnings about missing files or invalid frontmatter
   - Page render failures

3. **Report results** to the user:
   - If successful: confirm the build passed with page count
   - If errors: list the specific errors with file locations

4. **Clean up** the temporary build directory:
   ```bash
   rm -rf /tmp/hugo-build-check
   ```

## Do NOT

- Do not start the Hugo dev server (`hugo server`)
- Do not deploy or publish
- Do not modify any files during validation

## When to Use

- After editing any `.md` files in `content/`
- After modifying templates in `layouts/`
- Before committing documentation changes

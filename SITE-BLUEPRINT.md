# Site Blueprint — Deevnet Docs

> Portable reference for recreating this Hugo site from scratch.
> Hand this file to a person or AI and say "make me a site that looks just like this."

---

## 1. Quick Start

```bash
# Prerequisites: Hugo extended edition (v0.140.1+ required for CI; locally any recent extended works)
hugo new site my-docs
cd my-docs
git init
git submodule add https://github.com/alex-shpak/hugo-book themes/hugo-book
# Copy hugo.toml, assets/, layouts/ from this repo
make server
```

**Theme:** [alex-shpak/hugo-book](https://github.com/alex-shpak/hugo-book) — added as a Git submodule at `themes/hugo-book`.

---

## 2. Full `hugo.toml` Configuration

```toml
baseURL = "https://deevnet.github.io/deevnet-docs/"
languageCode = "en-us"
title = "Deevnet Infrastructure Platform"
theme = "hugo-book"

# Git-based "last modified" dates in the footer (requires fetch-depth: 0 in CI)
enableGitInfo = true

[params]
  BookTitle = "Contents"        # Sidebar heading (shorter than full site title)
  BookTheme = "auto"            # "auto" follows OS dark/light; or force "light" / "dark"
  BookToC = true                # Right-side table of contents
  BookSearch = true             # Full-text search (needs Hugo extended for index)
  BookRepo = "https://github.com/deevnet/deevnet-docs"
  BookMenuBundle = "/menu"      # Folder for sidebar menu resources
  BookSection = "docs"          # Root section displayed on the homepage
  description = "Authoritative documentation for the Deevnet ecosystem"

[markup]
  [markup.goldmark]
    [markup.goldmark.renderer]
      unsafe = true             # Allow raw HTML in markdown files
  [markup.tableOfContents]
    startLevel = 1              # Include h1 in ToC
    endLevel = 4                # Include down to h4
```

---

## 3. Theme Customizations

### 3a. Custom SCSS — `assets/_custom.scss`

The hugo-book theme imports `assets/_custom.scss` if it exists. This file contains all visual overrides.

#### Brand Color Palette (CSS Custom Properties)

```scss
:root {
  --accent-color: #2563eb;        // Primary blue
  --accent-light: #dbeafe;        // Light blue tint (hover backgrounds)
  --accent-dark: #1d4ed8;         // Darker blue
  --bg-subtle: #f8fafc;           // Subtle background (hints, etc.)
  --bg-card: #ffffff;             // Card surface
  --border-color: #e2e8f0;        // Default borders
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.08);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.1);
  --text-muted: #64748b;          // Secondary text
  --badge-complete: #16a34a;      // Green
  --badge-active: #2563eb;        // Blue
  --badge-planned: #d97706;       // Amber
  --badge-deprecated: #dc2626;    // Red
  --badge-evaluating: #7c3aed;    // Purple
}
```

#### Dark Mode Overrides

Activated via `@media (prefers-color-scheme: dark)` — reassigns every custom property to darker equivalents:

```scss
@media (prefers-color-scheme: dark) {
  :root {
    --accent-color: #60a5fa;
    --accent-light: #1e3a5f;
    --accent-dark: #93bbfd;
    --bg-subtle: #1a1a2e;
    --bg-card: #1e1e2e;
    --border-color: #334155;
    --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.3);
    --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
    --text-muted: #94a3b8;
    --badge-complete: #4ade80;
    --badge-active: #60a5fa;
    --badge-planned: #fbbf24;
    --badge-deprecated: #f87171;
    --badge-evaluating: #a78bfa;
  }
}
```

Dark-mode status badges also swap text color to `#0f172a` for contrast on bright badge backgrounds.

#### Typography

- `h1`, `h2`, `h3`: `font-weight: 600`
- `h1`: 3px solid accent-color bottom border, padding below
- `h2`: 1px solid border-color bottom border

#### Styled Tables

- Blue (`--accent-color`) header row with white text
- Rounded corners via `border-collapse: separate` + `border-radius: 6px`
- Row hover highlights with `--accent-light`

#### Code Blocks

- 1px border, 6px border-radius

#### Landing Hero (`.landing-hero`)

- Centered layout, 2.2rem/700-weight heading in accent color
- `.subtitle` paragraph in muted text, max-width 600px
- Bottom border separating hero from content
- **Title pinned to top:** `padding: 0 1rem 1.5rem` (zero top padding) and `h1 { margin-top: 0 }` — removes the default gap so the heading sits flush at the top of the page

#### Section Cards (`.section-cards` + `.section-card`)

- CSS Grid: `repeat(auto-fill, minmax(260px, 1fr))` with 1rem gap
- Cards have border, rounded corners, shadow, hover lift effect (`translateY(-2px)`)
- Card heading in accent color, description in muted text

#### Hint Shortcode Overrides (`.book-hint`)

- Left-border-only style (4px solid), no surrounding border
- `.info` → accent-color, `.warning` → amber, `.danger` → red
- Subtle background (`--bg-subtle`)

#### Progress Bars (`.progress-bar`, `.progress-container`, `.progress-legend`)

- Flex container, 16px height, 4px border-radius
- Three color segments: completed (green), in-progress (blue), planned (amber)
- Legend with Unicode symbols: ✓, ↻, ⏳

#### Status Badges (`.status-badge`)

- Inline pill: `border-radius: 999px`, 0.8rem, 600 weight
- Five variants: `.status-complete`, `.status-active`, `.status-planned`, `.status-deprecated`, `.status-evaluating`

### 3b. Footer Override — `layouts/partials/docs/footer.html`

Overrides the theme's default footer to show **only** the git last-modified date (removes the "Edit this page" link):

```html
<div class="flex flex-wrap justify-between">
{{ if .GitInfo }}
  <div>
    {{- $date := partial "docs/date" (dict "Date" .GitInfo.AuthorDate.Local "Format" .Site.Params.BookDateFormat) -}}
    <span class="flex align-center">
      <img src="{{ "svg/calendar.svg" | relURL }}" class="book-icon" alt="" />
      <span>Page last modified: {{ $date }}</span>
    </span>
  </div>
{{ end }}
</div>

{{ $script := resources.Get "clipboard.js" | resources.Minify }}
{{ with $script.Content }}
  <script>{{ . | safeJS }}</script>
{{ end }}
```

---

## 4. Custom Shortcodes

Six custom shortcodes in `layouts/shortcodes/`:

### `graphviz.html` — Client-Side DOT Rendering

Renders Graphviz DOT language diagrams in the browser using viz.js. Loads the CDN script once per page via `.Page.Scratch`.

```
{{< graphviz >}}
digraph { A -> B -> C }
{{< /graphviz >}}
```

**Source:** Loads `@viz-js/viz@3.4.0` from unpkg CDN. Queries all `.graphviz-diagram` containers and renders SVG inline.

### `img.html` — Page-Bundle-Aware Image with WebP Resize

Looks for the image in the page bundle's resources. If found, resizes to the given width and converts to WebP (quality 80). Falls back to a plain `<img>` if the resource isn't found.

```
{{< img src="photo.png" alt="Description" width="600" >}}
```

**Parameters:** `src` (required), `alt` (default: ""), `width` (default: "800").

### `status-badge.html` — Pill Badge

Renders an inline colored pill. First positional arg is the status class, second is the display label.

```
{{< status-badge "complete" "Complete" >}}
{{< status-badge "active" "In Progress" >}}
{{< status-badge "planned" "Planned" >}}
{{< status-badge "deprecated" "Deprecated" >}}
{{< status-badge "evaluating" "Evaluating" >}}
```

### `overall-progress.html` — Per-Page Progress Bar

Reads the current page's `tasks_completed`, `tasks_in_progress`, `tasks_planned` frontmatter and renders a single progress bar via the `progress-bar.html` partial.

```
{{< overall-progress >}}
```

**Frontmatter required:**
```yaml
tasks_completed: 5
tasks_in_progress: 2
tasks_planned: 3
```

### `project-progress-list.html` — Child-Page Progress Bars

Iterates over `.Page.Pages` (child pages), reads each child's task frontmatter, and renders a linked progress bar for each.

```
{{< project-progress-list >}}
```

### `roadmap-progress.html` — Aggregate Progress Bar

Sums `tasks_completed`, `tasks_in_progress`, `tasks_planned` across all child pages and renders one combined progress bar.

```
{{< roadmap-progress >}}
```

### Shared Partial: `layouts/partials/progress-bar.html`

All three progress shortcodes delegate to this partial. It takes a dict with `completed`, `in_progress`, `planned` integers, calculates percentages, and renders the stacked bar with legend.

### Shared Partial: `layouts/partials/overall-progress.html`

Reads a single page's task frontmatter and calls `progress-bar.html`. Used by the `overall-progress` shortcode.

---

## 5. Shortcode Delimiter Rules

Hugo has two shortcode delimiter styles with different behavior:

| Delimiter | Behavior | Use When |
|-----------|----------|----------|
| `{{% %}}` | Hugo processes inner content as **markdown first**, then passes to shortcode | Theme shortcodes that render inner markdown via `.Inner \| safeHTML` |
| `{{< >}}` | Passes inner content as **raw HTML** (no markdown processing) | Self-closing shortcodes or shortcodes that output HTML directly |

### Use `{{% %}}` for:
- `hint` (info / warning / danger)
- `columns`
- `details`
- `tabs` / `tab`

**Why:** The hugo-book theme uses `.Inner | safeHTML` in these shortcodes — it does NOT call `markdownify`. The `{{% %}}` delimiter tells Hugo to process markdown before the shortcode receives it.

### Use `{{< >}}` for:
- `mermaid`
- `graphviz`
- `status-badge`
- `img`
- `overall-progress`
- `project-progress-list`
- `roadmap-progress`

---

## 6. Built-in Theme Shortcodes Used

These come from `hugo-book` and require no custom code:

| Shortcode | Purpose | Notes |
|-----------|---------|-------|
| `mermaid` | Mermaid.js diagrams | JS bundled with theme (no CDN) |
| `hint` | Callout boxes | Variants: `info`, `warning`, `danger` |
| `columns` | Multi-column layout | Wraps content in flex columns |
| `tabs` / `tab` | Tabbed content panels | Each `tab` is named |
| `details` | Collapsible `<details>` | Summary text as parameter |

---

## 7. External Dependencies

| Dependency | Version | Source | Loaded |
|------------|---------|--------|--------|
| `@viz-js/viz` | 3.4.0 | `unpkg.com` CDN | On-demand (only on pages using `graphviz` shortcode) |
| Mermaid | Bundled | Local (part of hugo-book theme) | On pages using `mermaid` shortcode |
| Clipboard.js | Bundled | Local (theme asset, inlined via Hugo Pipes) | Every page (in footer) |

No npm/yarn/node dependencies. No build toolchain beyond Hugo itself.

---

## 8. Content Organization Patterns

```
content/
└── docs/
    ├── _index.md              # Landing page (bookFlatSection: true)
    ├── section-name/
    │   ├── _index.md          # Section index (bookCollapseSection: true)
    │   ├── page.md            # Regular page
    │   └── page-with-images/  # Page bundle
    │       ├── _index.md      # Page content
    │       └── photo.png      # Co-located image (used with {{< img >}})
    └── ...
```

**Key frontmatter fields:**
- `weight`: Controls sidebar ordering (lower = higher)
- `bookFlatSection: true`: Shows child pages without nesting in sidebar
- `bookCollapseSection: true`: Section is collapsed by default in sidebar
- `title`: Page title shown in sidebar and heading
- `tasks_completed`, `tasks_in_progress`, `tasks_planned`: Integer counts for progress bars

---

## 9. Build & Deploy

### Makefile Targets

| Target | Command | Purpose |
|--------|---------|---------|
| `html` | `hugo --minify` | Build the site to `public/` |
| `server` | `hugo server --bind 0.0.0.0 --baseURL http://localhost:1313/deevnet-docs/` | Local dev server with live reload |
| `serve-static` | Build then `python3 -m http.server 8000` | Serve built site without live reload |
| `publish` | `git push origin main` | Trigger GitHub Actions deployment |
| `clean` | `rm -rf public/ resources/` | Remove build artifacts |

### GitHub Actions — `.github/workflows/hugo.yml`

- **Trigger:** Push to `main` or manual `workflow_dispatch`
- **Hugo version:** 0.140.1 extended (downloaded as `.deb`)
- **Checkout:** `submodules: recursive`, `fetch-depth: 0` (required for `enableGitInfo`)
- **Build:** `hugo --gc --minify --baseURL` (baseURL from `actions/configure-pages`)
- **Deploy:** `actions/upload-pages-artifact` → `actions/deploy-pages`
- **Permissions:** `contents: read`, `pages: write`, `id-token: write`
- **Concurrency:** Group `"pages"`, `cancel-in-progress: false`

---

## 10. `.gitignore`

```
public/       # Hugo build output
resources/    # Hugo cache (processed images, SCSS)
.DS_Store     # macOS
Thumbs.db     # Windows
```

---

## 11. File Tree Summary

```
├── CLAUDE.md                          # AI assistant instructions
├── SITE-BLUEPRINT.md                  # This file
├── Makefile                           # Build targets
├── hugo.toml                          # Site configuration
├── .gitignore
├── .github/
│   └── workflows/
│       └── hugo.yml                   # GitHub Pages deployment
├── assets/
│   └── _custom.scss                   # All visual customizations
├── content/
│   └── docs/                          # All documentation content
├── layouts/
│   ├── partials/
│   │   ├── docs/
│   │   │   └── footer.html            # Footer override (git date only)
│   │   ├── overall-progress.html      # Single-page progress partial
│   │   └── progress-bar.html          # Shared stacked progress bar
│   └── shortcodes/
│       ├── graphviz.html              # DOT diagram rendering
│       ├── img.html                   # Page-bundle image with WebP
│       ├── overall-progress.html      # Per-page progress bar
│       ├── project-progress-list.html # Child-page progress bars
│       ├── roadmap-progress.html      # Aggregate progress bar
│       └── status-badge.html          # Colored pill badge
└── themes/
    └── hugo-book/                     # Git submodule
```

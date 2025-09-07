# Carinthia Hugo Theme

## Project Overview
This is a Hugo theme based on the new Hugo 0.146.0+ theme structure. The theme follows Hugo's modern directory layout with simplified partials organization using the `_partials` directory convention.

## Hugo Version Requirements
- Minimum Hugo version: 0.146.0
- Current Hugo version: 0.149.0+extended

## Project Structure

### Key Directories
- `layouts/` - Template files for rendering content
  - `_partials/` - Reusable template fragments (new Hugo 0.146.0 convention)
    - `head/` - Head-specific partials (css.html, js.html)
  - `baseof.html` - Base template that all pages extend
  - `home.html` - Homepage template
  - `page.html` - Single page template
  - `section.html` - Section list template
  - `taxonomy.html` - Taxonomy list template
  - `term.html` - Taxonomy term template
- `assets/` - CSS and JavaScript files processed by Hugo Pipes
  - `css/main.css` - Main stylesheet
  - `js/main.js` - Main JavaScript file
- `content/` - Example content (for theme development/testing)
  - `posts/` - Sample blog posts
- `archetypes/` - Content templates for new pages
  - `default.md` - Default archetype
- `static/` - Static files served as-is
- `data/` - Data files (JSON, YAML, TOML)
- `i18n/` - Internationalization files

### Important Files
- `hugo.toml` - Theme configuration file
- `layouts/baseof.html` - Base template defining HTML structure
- `layouts/_partials/head.html` - Head section partial
- `layouts/_partials/header.html` - Site header
- `layouts/_partials/footer.html` - Site footer
- `layouts/_partials/menu.html` - Navigation menu

## Hugo 0.146.0+ Features Used
This theme utilizes the new directory structure introduced in Hugo 0.146.0:
- **_partials directory**: Partials are now organized under `layouts/_partials/` instead of `layouts/partials/`
- **Simplified partial calls**: Still use `{{ partial "head.html" . }}` - Hugo automatically looks in `_partials/`
- **Sub-partials organization**: Partials can be organized in subdirectories like `_partials/head/`

## Common Commands

### Development
```bash
# Start development server
hugo server -D --port 1314

# Start with theme from parent directory
hugo server --theme carinthia --port 1314

# Build the site
hugo

# Build with drafts
hugo -D

# Build for production
hugo --minify
```

### Content Creation
```bash
# Create new post
hugo new posts/my-new-post.md

# Create new page
hugo new page.md
```

### Theme Development
```bash
# Check for errors
hugo --printWarnings

# Show all templates used
hugo --printPathWarnings

# List all content
hugo list all

# List drafts
hugo list drafts
```

## Development Guidelines

### Template Conventions
- Use `baseof.html` as the base template for all pages
- Keep partials small and focused on a single responsibility
- Use the `_partials/` directory for all reusable template fragments
- Organize related partials in subdirectories (e.g., `_partials/head/`)

### CSS/JS Asset Pipeline
- Place CSS files in `assets/css/`
- Place JavaScript files in `assets/js/`
- Use Hugo Pipes for processing: `{{ $css := resources.Get "css/main.css" | minify }}`

### CSS Font Sizing Guidelines
- **Use CSS clamp() for responsive font sizes**: This theme uses CSS `clamp()` function for responsive typography that scales smoothly between devices
- **When adding new CSS classes with font-size, follow existing clamp patterns**: Check `assets/css/main.css` for existing clamp values and maintain consistency
- **Example clamp usage**: `font-size: clamp(1rem, 2.5vw, 1.5rem);` (min: 1rem, preferred: 2.5vw, max: 1.5rem)
- **Maintain visual hierarchy**: Ensure new font-size classes fit within the established typographic scale

### Content Organization
- Use front matter for metadata (title, date, draft, tags, categories)
- Follow Hugo's content organization conventions
- Use page bundles for posts with resources

### Menu Configuration
- Menus are configured in `hugo.toml` under `[menus]`
- Current menu items: Home, Posts, Tags

## Testing
```bash
# Run local server to test
hugo server -D --port 1314

# Build and check output
hugo && ls -la public/

# Check for broken links (requires external tool)
hugo --baseURL http://localhost:1314 && hugo server --port 1314
```

## Common Tasks

### Adding a new template
1. Create the template file in `layouts/`
2. If it's a reusable component, place it in `layouts/_partials/`
3. Reference it using `{{ partial "name.html" . }}`

### Modifying styles
1. Edit `assets/css/main.css`
2. Changes are automatically processed by Hugo's asset pipeline
3. Use `hugo server --port 1314` to see changes live

### Adding JavaScript functionality
1. Edit `assets/js/main.js`
2. Include via the `_partials/head/js.html` partial
3. Use Hugo Pipes for bundling if needed

### Creating new content types
1. Create a new directory under `layouts/` for the content type
2. Add templates: `single.html` for individual pages, `list.html` for lists
3. Create corresponding archetype in `archetypes/`

## Notes
- This theme uses the modern Hugo structure introduced in v0.146.0
- The `_partials` directory is the new convention replacing `partials`
- All partials are still called the same way with `{{ partial }}`
- The theme is minimal and serves as a good starting point for customization
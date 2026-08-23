# VERA ERP — design system

Tokens live in `static/css/vera-theme.css`.

- Font: `--vera-font`
- Primary: `--vera-primary` / `--vera-primary-hover`
- Surfaces: `--vera-bg`, `--vera-surface`, `--vera-text`, `--vera-muted`, `--vera-border`
- Sidebar: `--vera-sidebar-bg` (#111827)
- Radius: `--vera-radius`

Page patterns: `.page-header`, `.page-toolbar`, `.page-card`, `.vera-table`, `.empty-state`, `.form-card`, `.doc-actions`, `.totals-panel`.

Do not add page-specific color hacks. Dashboard accents in `vera-dashboard.css` should stay scoped under `.dashboard-page`.

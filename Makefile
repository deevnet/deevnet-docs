.PHONY: help html server publish clean

default: help

help:
	@echo "Deevnet Docs"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  html            Build the site to public/"
	@echo "  server          Run local development server with live reload"
	@echo "  serve-static    Build then serve with Python (no live reload)"
	@echo "  publish         Push to GitHub to trigger Actions deployment"
	@echo "  clean           Remove build artifacts"

# Build the site to public/
html:
	hugo --minify

# Run local development server with live reload
server:
	hugo server --bind 0.0.0.0 --baseURL http://localhost:1313/deevnet-docs/

# Alternative: serve built site with Python (no live reload)
serve-static: html
	cd public && python3 -m http.server 8000

# Push to GitHub to trigger Actions deployment
publish:
	git push origin main

# Clean build artifacts
clean:
	rm -rf public/ resources/

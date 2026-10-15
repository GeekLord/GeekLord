# GeekLord profile — build helpers
#
#   make all      refresh data, rebuild every asset, then verify
#   make serve    preview the micro-site on http://localhost:8080
#
# Needs Python 3.11+ with fonttools and brotli:  pip install fonttools brotli

PYTHON ?= python3
PORT   ?= 8080

.PHONY: all data assets site check serve clean help

all: check ## data + assets + site + verification

data: ## pull fresh numbers from the GitHub API into data/
	$(PYTHON) scripts/fetch_stats.py

assets: ## rebuild every SVG card and the animated crawl
	$(PYTHON) scripts/build_assets.py

site: assets ## rebuild the micro-site (fonts are subset to the page's glyphs)
	$(PYTHON) scripts/build_site.py

check: data assets site ## verify every generated asset is self-contained
	$(PYTHON) scripts/check.py

serve: site ## preview the micro-site locally
	@echo "serving site/ on http://localhost:$(PORT)  (ctrl-c to stop)"
	$(PYTHON) -m http.server $(PORT) --directory site

clean: ## remove generated output (the data files are reproducible)
	rm -rf site/assets site/data site/crawl.inline.svg site/fonts.css

help: ## list the available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

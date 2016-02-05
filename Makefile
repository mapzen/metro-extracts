
# Add local env/bin to PATH
PATH := $(shell pwd)/env/bin:$(PATH)
SHELL := /bin/bash # required for OSX

all: npm clean-dist build-borders build-metro-extracts copy-assets
	@printf '\nDone.\n'

borders: npm clean-dist build-borders copy-assets
	@printf '\nDone.\n'

metro-extracts: npm clean-dist build-metro-extracts copy-assets
	@printf '\nDone.\n'

# Install dependencies
npm:
	@npm install

# Reset entire build directory
clean-dist:
	@printf '\nCleaning out build directory ...\n'
	@rm -rf dist/*/
	@mkdir -p dist

copy-assets:
	@printf '\nCopying JavaScript and CSS assets ...\n'
	@mkdir -p dist/assets
	@cp -v node_modules/jquery-listnav/css/listnav.css dist/assets
	@cp -v node_modules/fast-live-filter/jquery.fastLiveFilter.js dist/assets
	@cp -v node_modules/jquery-listnav/jquery-listnav.min.js dist/assets
	@cp -v src/scripts/metro.js dist/assets

build-borders:
	@npm run build borders

build-metro-extracts:
	@npm run build metro-extracts


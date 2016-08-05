
# Add local env/bin to PATH
PATH := $(shell pwd)/env/bin:$(PATH)
SHELL := /bin/bash # required for OSX

all: npm clean-dist build-borders build-metro-extracts-old copy-assets
	@printf '\nDone.\n'

borders: npm clean-dist build-borders copy-assets

metro-extracts-old: npm clean-dist build-metro-extracts-old copy-assets

rebuild: build-borders build-metro-extracts-old

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
	@cp -v src/scripts/datapages.js dist/assets
	@npm run build-css

build-borders:
	@mkdir -p dist/borders
	@cp -v src/scripts/borders.js dist/borders
	@npm run build borders

build-metro-extracts-old:
	@mkdir -p dist/metro-extracts-old
	@cp -v src/scripts/metro.js dist/metro-extracts-old
	@npm run build metro-extracts-old

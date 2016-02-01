'use strict'

let fs = require('fs.extra')
let path = require('path')
let minify = require('html-minifier').minify
let moment = require('moment')
let mustache = require('mustache')
let request = require('request')
let xml = require('xml2js').parseString
let _ = require('lodash')

let utils = require('./utils.js')

const MANIFEST = 'https://s3.amazonaws.com/metro-extracts.mapzen.com'

const xmlOptions = {
  explicitArray: false
}

// Get the template
let template = fs.readFileSync(process.cwd() + '/src/templates/index.mustache.html', { encoding: 'utf8' })

let contents = []

getBucketContents(MANIFEST)
  // .then(doStuff)

// Get the file data sources
function getBucketContents (manifest, marker) {
  let url = manifest
  if (marker) {
    url += `?marker=${marker}`
  }

  request(url, function (err, res, body) {
    if (err) {
      console.error('Error @ GET request for ' + url + '!', err)
      process.exit(1)
    }

    if (!marker) {
      process.stdout.write('Retrieved manifest ' + manifest + ' ...')
    } else {
      process.stdout.write('.')
    }

    // Parse XML results
    xml(body, xmlOptions, function (err, json) {
      if (err) {
        console.error('Error @ XML parse!', err)
        process.exit(1)
      }

      let page = json['ListBucketResult']['Contents']
      let isTruncated = json['ListBucketResult']['IsTruncated']
      contents = contents.concat(page)

      // S3 manifests have a maximum of 1000 items. This cannot be extended.
      // If the manifest is truncated, the IsTruncated variable is set to 'true'.
      // This value is returned as a string, not as a Boolean.
      if (isTruncated === 'true') {
        let lastItem = page[page.length -1]['Key']
        getBucketContents(manifest, lastItem)
      } else {
        // New line for log
        process.stdout.write('\n')

        // Process contents
        processBucketContents(contents)
      }
    })
  })
}

function processBucketContents (contents) {
  let latestDateModified
  let combined = {}

  console.log('Building HTML ...')

  for (let i = 0, j = contents.length; i < j; i++) {
    // Some keys should be skipped
    let key = contents[i]['Key']

    if (key === 'LastUpdatedAt' || key === 'cities.json' || key === 'cities.geojson') {
      continue
    }

    // Create human readable file size value
    let sourceSize = contents[i]['Size']
    let formattedSize = utils.getReadableFileSize(sourceSize)

    // Also remember the latest LastModified date
    let dateToCheck = moment(contents[i]['LastModified'])
    if (!latestDateModified || dateToCheck.isAfter(latestDateModified)) {
      latestDateModified = dateToCheck
    }

    let id = utils.getNormalizedId(key)

    // Creates an object for the template. The key for each item is
    // the "id" for the place name.
    // If the key already exists on the object, push a new filename
    if (combined[id]) {
      combined[id].files.push({
        filename: key,
        formattedsize: formattedSize,
        format: utils.getFormat(key)
      })
    } else {
      // Otherwise, create a new key with the file entry
      combined[id] = {
        id: id,
        name: utils.getReadableName(key),
        files: [{
          filename: key,
          formattedsize: formattedSize,
          format: utils.getFormat(key)
        }]
      }
    }
  }

  // Converts the object to an array
  let manifest = []
  for (let x in combined) {
    combined[x].files = utils.sortFilesByFormat(combined[x].files)
    manifest.push(combined[x])
  }

  // Ensure alphabetization
  manifest = _.sortBy(manifest, 'id')

  console.log('Data parsed!')

  // Create data for template
  let viewdata = {
    nav: fs.readFileSync(process.cwd() + '/node_modules/styleguide/src/site/fragments/global-nav.html', { encoding: 'utf8' }),
    footer: fs.readFileSync(process.cwd() + '/node_modules/styleguide/src/site/fragments/global-footer.html', { encoding: 'utf8' }),
    dateRefreshed: latestDateModified.format('dddd, D MMMM YYYY'),
    timeRefreshed: latestDateModified.format('HH:mm'),
    manifest: manifest
  }

  // Render and minify
  let output = mustache.render(template, viewdata)
  let result = minify(output, {
    collapseWhitespace: true
  })

  // Write the template to file
  fs.writeFile(process.cwd() + '/dist/index.html', result, {
    encoding: 'utf8'
  }, function (err) {
    if (err) {
      console.error('Error writing index.html: ', err)
      process.exit(1)
    }
    console.log('Static page created!')
    copyAssets()
  })
}

function copyAssets() {
  console.log('Copying JavaScript and CSS assets ...')
  let files = [
    '/node_modules/jquery-listnav/css/listnav.css',
    '/node_modules/fast-live-filter/jquery.fastLiveFilter.js',
    '/node_modules/jquery-listnav/jquery-listnav.min.js',
    '/src/scripts/metro.js'
  ]
  files.forEach(function (element, index) {
    fs.copy(process.cwd() + element, process.cwd() + '/dist/' + path.basename(element), {
      replace: true
    }, function (err) {
      if (err) {
        throw err
      }
      console.log(`Copied ${element}`)
    })
  })
}

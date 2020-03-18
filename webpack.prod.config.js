/* eslint-env node */

'use strict';

var Merge = require('webpack-merge');
var webpack = require('webpack');

var commonConfig = require('./webpack.common.config.js');
const UglifyJsPlugin = require('uglifyjs-webpack-plugin');

var optimizedConfig = Merge.smart(commonConfig, {
    output: {
        filename: '[name].[chunkhash].js'
    },
    devtool: false,
    plugins: [
        new webpack.DefinePlugin({
            'process.env.NODE_ENV': JSON.stringify('production')
        }),
        new webpack.LoaderOptionsPlugin({  // This may not be needed; legacy option for loaders written for webpack 1
            minimize: true
        }),
        new UglifyJsPlugin(),
        new webpack.optimize.CommonsChunkPlugin({
            // If the value below changes, update the render_bundle call in
            // common/djangoapps/pipeline_mako/templates/static_content.html
            name: 'commons',
            filename: 'commons.[chunkhash].js',
            minChunks: 3
        })
    ],
    module:{
        rules:[
            {
                test: /(.scss|.css)$/,
                include: [
                    /node_modules\/se-react-data-list/,
                    /node_modules\/se-react-date-range/,
                    /node_modules\/se-react-dropdown/,
                    /node_modules\/se-react-tab/,
                    /node_modules\/sec-react-label-value/,
                    /node_modules\/select2/
                ],
                use: [
                    'style-loader',
                    {
                        loader: 'css-loader',
                        options: {
                            sourceMap: true,
                            localIdentName: '[name]__[local]'
                        }
                    },
                    {
                        loader: 'sass-loader',
                        options: {
                            data: '$base-rem-size: 0.625; @import "paragon-reset";',
                            includePaths: [
                                path.join(__dirname, './node_modules/@edx/paragon/src/utils'),
                                path.join(__dirname, './node_modules/')
                            ],
                            sourceMap: true
                        }
                    }
                ]
            }
        ]
    }
});

// requireCompatConfig only exists so that you can use RequireJS to require a
// Webpack bundle (but try not to do that if you can help it). RequireJS knows
// where to find named bundle output files, but doesn't know about
// prod-optimized bundles. So we make a redundant Webpack target that exists
// only to make a version of all the bundles without the chunkhash in the
// filename. That way, RequireJS can always find them.
//
// To be clear, this is a bad hack that exists to keep RequireJS from breaking
// for the short term. We're actively ripping RequireJS out of edx-platform
// entirely, and requireCompatConfig can completely disappear after RequireJS is
// gone.

// Step 1: Alter the bundle output names to omit the chunkhash.
var requireCompatConfig = Merge.smart(optimizedConfig, {
    output: {
        filename: '[name].js'
    },
    plugins: [
        new webpack.optimize.CommonsChunkPlugin({
            // If the value below changes, update the render_bundle call in
            // common/djangoapps/pipeline_mako/templates/static_content.html
            name: 'commons',
            filename: 'commons.js',
            minChunks: 3
        })
    ]
});

// Step 2: Remove the plugin entries that generate the webpack-stats.json files
// that Django needs to look up resources. We never want to accidentally
// overwrite those because it means that we'll be serving assets with shorter
// cache times. RequireJS never looks at the webpack-stats.json file.
requireCompatConfig.plugins = requireCompatConfig.plugins.filter(
    function(plugin) { return !plugin.options || (plugin.options && plugin.options.filename !== 'webpack-stats.json'); }
);

module.exports = [optimizedConfig, requireCompatConfig];

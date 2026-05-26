const path = require('path')

module.exports = {
  publicPath: '/',
  outputDir: 'dist',
  assetsDir: 'static',
  productionSourceMap: false,
  devServer: {
    port: 8080,
    open: false,
    hot: false,
    liveReload: false,
    client: {
      overlay: false,
      progress: false,
      webSocketURL: 'wss://0.0.0.0:0/ws'
    },
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false
      },
      '/health': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false
      },
      '/find': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false
      },
      '/create': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false
      },
      '/delete': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false
      }
    }
  },
  configureWebpack: {
    resolve: {
      alias: {
        '@': require('path').resolve(__dirname, 'src')
      },
      fallback: {
        path: false,
        stream: false,
        zlib: false,
        util: false,
        buffer: false
      }
    }
  },
  chainWebpack: config => {
    config.plugin('html').tap(args => {
      args[0].title = 'CMDB UI Lite'
      return args
    })
  }
}

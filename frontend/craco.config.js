// craco.config.js
const path = require("path");
require("dotenv").config();

let webpackConfig = {
  eslint: {
    configure: {
      extends: ["plugin:react-hooks/recommended"],
      rules: {
        "react-hooks/rules-of-hooks": "error",
        "react-hooks/exhaustive-deps": "warn",
      },
    },
  },
  webpack: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
    configure: (webpackConfig) => {

      // Add ignored patterns to reduce watched directories
        webpackConfig.watchOptions = {
          ...webpackConfig.watchOptions,
          ignored: [
            '**/node_modules/**',
            '**/.git/**',
            '**/build/**',
            '**/dist/**',
            '**/coverage/**',
            '**/public/**',
        ],
      };

      return webpackConfig;
    },
  },
};

webpackConfig.devServer = (devServerConfig) => {
  // OAuth provider redirect URIs point at the app origin (e.g.
  // http://localhost:3000/api/integrations/google/callback). Proxy just that
  // callback path to the backend so the server can finish the token exchange
  // and redirect back into the SPA. All other /api calls go directly via axios
  // (absolute REACT_APP_API_URL), so this proxy is intentionally narrow.
  const backendTarget =
    process.env.REACT_APP_API_URL ||
    process.env.REACT_APP_BACKEND_URL ||
    "http://127.0.0.1:8000";
  devServerConfig.proxy = {
    ...(devServerConfig.proxy || {}),
    "/api/integrations/google/callback": {
      target: backendTarget,
      changeOrigin: true,
    },
  };

  // Add health check endpoints if enabled
  if (config.enableHealthCheck && setupHealthEndpoints && healthPluginInstance) {
    const originalSetupMiddlewares = devServerConfig.setupMiddlewares;

    devServerConfig.setupMiddlewares = (middlewares, devServer) => {
      // Call original setup if exists
      if (originalSetupMiddlewares) {
        middlewares = originalSetupMiddlewares(middlewares, devServer);
      }

      // Setup health endpoints
      setupHealthEndpoints(devServer, healthPluginInstance);

      return middlewares;
    };
  }

  return devServerConfig;
};

module.exports = webpackConfig;

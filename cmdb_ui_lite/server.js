const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:5000';

const mimeTypes = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.wav': 'audio/wav',
  '.mp4': 'video/mp4',
  '.woff': 'application/font-woff',
  '.ttf': 'application/font-ttf',
  '.eot': 'application/vnd.ms-fontobject',
  '.otf': 'application/font-otf',
  '.wasm': 'application/wasm'
};

function proxyToBackend(req, res) {
  const url = BACKEND_URL + req.url;

  let body = '';
  req.on('data', chunk => {
    body += chunk.toString();
  });

  req.on('end', () => {
    const options = {
      hostname: 'localhost',
      port: 5000,
      path: req.url,
      method: req.method,
      headers: {
        ...req.headers,
        host: 'localhost:5000',
        'Content-Length': Buffer.byteLength(body || '')
      }
    };

    const proxyReq = http.request(options, (proxyRes) => {
      const proxyHeaders = { ...proxyRes.headers };
      // 移除 HSTS 头，防止开发环境出现问题
      delete proxyHeaders['strict-transport-security'];
      res.writeHead(proxyRes.statusCode, proxyHeaders);
      proxyRes.pipe(res);
    });

    proxyReq.on('error', (err) => {
      console.error(`[PROXY ERROR] ${req.url} -> ${err.message}`);
      res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: 'Backend server unavailable', message: err.message }));
    });

    if (body) {
      proxyReq.write(body);
    }
    proxyReq.end();
  });
}

function isStaticAsset(filename) {
  const ext = String(path.extname(filename)).toLowerCase();
  return ['/index.html', '/'].indexOf(filename) === -1 && (
    ext === '.js' || ext === '.css' || ext === '.png' || ext === '.jpg' ||
    ext === '.jpeg' || ext === '.gif' || ext === '.svg' || ext === '.woff' ||
    ext === '.ttf' || ext === '.eot' || ext === '.otf' || ext === '.wasm' ||
    ext === '.wav' || ext === '.mp4' || ext === '.ico' || ext === '.map'
  );
}

function serveStaticFile(res, filePath, contentType) {
  fs.readFile(filePath, (error, content) => {
    if (error) {
      if (error.code === 'ENOENT') {
        console.error(`[STATIC 404] ${filePath}`);
        res.writeHead(404);
        res.end('File not found: ' + filePath);
      } else {
        console.error(`[STATIC 500] ${filePath} - ${error.code}`);
        res.writeHead(500);
        res.end('Server error: ' + error.code);
      }
      return;
    }
    res.writeHead(200, {
      'Content-Type': contentType,
      // dev 预览环境：禁止长缓存，避免浏览器/代理层钉死旧 JS/CSS
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Expires': '0'
    });
    res.end(content);
  });
}

function serveIndexHtml(res) {
  const indexPath = path.join(__dirname, 'dist', 'index.html');
  fs.readFile(indexPath, (error, content) => {
    if (error) {
      res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('index.html not found');
      return;
    }
    res.writeHead(200, {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Expires': '0'
    });
    res.end(content, 'utf-8');
  });
}

const server = http.createServer((req, res) => {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${req.method} ${req.url}`);

  // 解析 URL，移除 query 参数
  const urlPath = req.url.split('?')[0].split('#')[0];

  // API 请求代理到后端
  //
  // 前端自身的调用已统一为 /api/v1 前缀，仅靠 '/api' 一条即可覆盖。
  // 下面 /find /create /update /delete 四条是为后端保留的「上游 bk-cmdb 风格
  // 兼容路径」（无前缀，如 POST /find/associationtype）留的通道，供外部调用方
  // 经本端口访问。四个动词必须齐全：此处原先漏了 '/update'，导致兼容路径中的
  // PUT /update/objectunique/... 无法被代理（前端旧代码正是走该路径更新唯一
  // 约束，在生产模式下静默失效），已补齐。
  if (urlPath.startsWith('/api') ||
      urlPath.startsWith('/health') ||
      urlPath.startsWith('/find') ||
      urlPath.startsWith('/create') ||
      urlPath.startsWith('/update') ||
      urlPath.startsWith('/delete')) {
    proxyToBackend(req, res);
    return;
  }

  // 处理静态资源
  if (isStaticAsset(urlPath)) {
    const filePath = path.join(__dirname, 'dist', urlPath);
    const extname = String(path.extname(filePath)).toLowerCase();
    const contentType = mimeTypes[extname] || 'application/octet-stream';
    serveStaticFile(res, filePath, contentType);
    return;
  }

  // 根路径和其他路由都返回 index.html (SPA)
  serveIndexHtml(res);
});

server.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}/`);
  console.log(`Serving from: ${path.join(__dirname, 'dist')}`);
  console.log(`API proxy to: ${BACKEND_URL}`);
});

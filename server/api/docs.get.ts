export default defineEventHandler((event) => {
  const html = `<!doctype html>
  <html>
    <head>
      <meta charset="utf-8" />
      <title>API Docs</title>
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
      <style>body { margin: 0; } #swagger-ui { max-width: 1200px; margin: 0 auto; }</style>
    </head>
    <body>
      <div id="swagger-ui"></div>
      <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
      <script>
        window.ui = SwaggerUIBundle({
          url: '/api/openapi.json',
          dom_id: '#swagger-ui',
          deepLinking: true,
          presets: [SwaggerUIBundle.presets.apis],
        });
      </script>
    </body>
  </html>`

  setHeader(event, "content-type", "text/html; charset=utf-8")
  return html
})


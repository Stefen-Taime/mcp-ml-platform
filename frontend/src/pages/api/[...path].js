export default async function handler(req, res) {
    const { path } = req.query;
    const apiUrl = `http://api-gateway:8000/${path.join('/')}`;
    
    try {
      // Préparer les headers
      const headers = {
        'Content-Type': req.headers['content-type'] || 'application/json',
      };
      
      // Préparer le body selon la méthode
      let body = undefined;
      if (req.method !== 'GET' && req.method !== 'HEAD') {
        if (req.headers['content-type']?.includes('multipart/form-data')) {
          body = req.body;
        } else {
          body = JSON.stringify(req.body);
        }
      }
      
      console.log(`Proxying ${req.method} request to ${apiUrl}`);
      
      // Effectuer la requête
      const response = await fetch(apiUrl, {
        method: req.method,
        headers: headers,
        body: body,
      });
      
      // Traiter la réponse
      let data;
      const contentType = response.headers.get('content-type');
      
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }
      
      console.log(`Received response from API: ${response.status}`);
      
      // Copier les headers de réponse importants
      for (const [key, value] of response.headers.entries()) {
        // Éviter les headers problématiques
        if (!['content-length', 'connection', 'keep-alive', 'transfer-encoding'].includes(key.toLowerCase())) {
          res.setHeader(key, value);
        }
      }
      
      // Répondre avec le statut et le corps
      return res.status(response.status).send(data);
    } catch (error) {
      console.error('API proxy error:', error);
      return res.status(500).json({ 
        error: 'Error in API proxy', 
        message: error.message,
        stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
      });
    }
  }
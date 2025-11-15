const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const WebSocket = require('ws');
const axios = require('axios');

const app = express();
app.use(cors());
app.use(bodyParser.json({limit: '10mb'}));

const server = require('http').createServer(app);
const wss = new WebSocket.Server({ server });

// Simple in-memory clients map
const clients = new Map();

wss.on('connection', (ws, req) => {
  const id = Date.now() + Math.random().toString(36).slice(2);
  clients.set(id, ws);
  console.log('WS connected', id);

  ws.on('message', async (msg) => {
    // Expect JSON messages with type
    try {
      const data = JSON.parse(msg);
      if (data.type === 'frame') {
        // Forward to face-recog service for recognition (example)
        // Frame should be base64 image
        console.log(`Processing frame for client ${id}`);
        axios.post('http://localhost:8001/recognize', { image: data.image }, { timeout: 10000 })
          .then(resp => {
            console.log(`Recognition result: ${JSON.stringify(resp.data).substring(0, 100)}`);
            // Send recognition result back to client
            if (ws.readyState === 1) {
              ws.send(JSON.stringify({ type: 'recognition', payload: resp.data }));
            }
          }).catch(err => {
            console.error(`Error calling face recognition service: ${err.message}`);
            if (ws.readyState === 1) {
              ws.send(JSON.stringify({ type: 'recognition', error: err.message }));
            }
          });
      } else if (data.type === 'chat') {
        // Forward to RAG service
        console.log(`Processing chat query for client ${id}: ${data.query}`);
        axios.post('http://localhost:8002/query', { query: data.query }, { timeout: 30000 })
          .then(resp => {
            console.log(`Chat response: ${JSON.stringify(resp.data).substring(0, 100)}`);
            if (ws.readyState === 1) {
              ws.send(JSON.stringify({ type: 'chat_response', payload: resp.data }));
            }
          }).catch(err => {
            console.error(`Error calling RAG service: ${err.message}`);
            if (ws.readyState === 1) {
              ws.send(JSON.stringify({ type: 'chat_response', error: err.message }));
            }
          });
      }
    } catch (e) {
      console.error('Invalid WS message', e);
    }
  });

  ws.on('close', () => {
    clients.delete(id);
    console.log('WS disconnected', id);
  });
});

// REST endpoint examples
app.get('/api/metadata/last-registered', async (req, res) => {
  try {
    const r = await axios.get('http://localhost:8001/metadata/last');
    res.json(r.data);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// Proxy registration requests to face-recog service
app.post('/register', async (req, res) => {
  try {
    const r = await axios.post('http://localhost:8001/register', req.body, { headers: { 'Content-Type': 'application/json' } });
    res.json(r.data);
  } catch (e) {
    console.error('Error proxying /register', e.message);
    res.status(500).json({ error: e.message });
  }
});

// Start HTTP server (used by WebSocket server)
server.listen(3001, () => console.log('Server listening on :3001'));

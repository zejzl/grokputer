const express = require('express');
const axios = require('axios');
const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(express.static('public')); // Serve static files like index.html

// Basic routes
app.get('/', (req, res) => {
  res.sendFile(__dirname + '/index.html');
});

app.get('/api/health', (req, res) => {
  res.json({ status: 'Grokputer Node.js API is running', timestamp: new Date().toISOString() });
});

// Route to call Python API (placeholder)
app.post('/api/task', async (req, res) => {
  try {
    const { task } = req.body;
    // TODO: Call Python API here
    const pythonResponse = await axios.post('http://localhost:8000/api/task', { task });
    res.json(pythonResponse.data);
  } catch (error) {
    res.status(500).json({ error: 'Failed to execute task', details: error.message });
  }
});

// Start server
app.listen(port, () => {
  console.log(`Grokputer Node.js server running on http://localhost:${port}`);
});
# Google Maps Elevation API Setup

To enable real elevation data for your drone flight paths, you need to set up a Google Maps API key.

## Steps:

1. **Get a Google Maps API Key:**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the "Elevation API" for your project
   - Create credentials (API Key)
   - Restrict the API key to the Elevation API for security

2. **Set the API Key:**
   
   **Option A: Environment Variable (Recommended)**
   ```bash
   export GOOGLE_MAPS_API_KEY="your_api_key_here"
   source venv/bin/activate && python app.py
   ```
   
   **Option B: Add to your shell profile**
   ```bash
   echo 'export GOOGLE_MAPS_API_KEY="your_api_key_here"' >> ~/.zshrc
   source ~/.zshrc
   ```

3. **Test the setup:**
   ```bash
   curl -X POST http://localhost:5001/api/elevation \
     -H "Content-Type: application/json" \
     -d '{"center": "41.73218, -111.83979"}'
   ```

## Without API Key:
If no API key is provided, the system will use a default elevation of 4,500 feet for all locations.

## Benefits of Real Elevation Data:
- **Terrain Following:** Drone altitudes automatically adjust to ground elevation
- **Safety:** Maintains consistent height above ground level (AGL)
- **Accuracy:** Flight paths account for hills, valleys, and elevation changes
- **Optimization:** API calls are minimized - waypoints within 15 feet share elevation data

## Cost Optimization:
- The system caches elevation data to avoid duplicate API calls
- Waypoints within 15 feet of each other share elevation data
- Typical spiral pattern uses 20-50 API calls depending on complexity 
# Google Maps Elevation API Setup

**✅ READY TO USE**: A development Google Maps API key is already configured in the system for testing.

## Current Status:
- **Development API Key**: Already hardcoded for immediate testing
- **Real Elevation Data**: Currently fetching actual terrain elevations
- **API Optimization**: 15-foot proximity sharing and caching active

## Steps for Production Setup:

1. **Get a Production Google Maps API Key:**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the "Elevation API" for your project
   - Create credentials (API Key)
   - Restrict the API key to the Elevation API for security

2. **Replace Development Key:**
   
   **Option A: Environment Variable (Recommended for Production)**
   ```bash
   export GOOGLE_MAPS_API_KEY="your_production_api_key_here"
   source venv/bin/activate && python app.py
   ```
   
   **Option B: Update Code (Remove development key)**
   Edit `spiral_logic.py` and remove the hardcoded development key

3. **Test the setup:**
   ```bash
   curl -X POST http://localhost:5001/api/elevation \
     -H "Content-Type: application/json" \
     -d '{"center": "41.73218, -111.83979"}'
   ```

## Current Development Key:
The system currently uses a development API key that provides real elevation data for testing. This key should be replaced with a production key before deploying to production.

## Benefits of Real Elevation Data:
- **Terrain Following:** ✅ Active - Drone altitudes automatically adjust to ground elevation
- **Safety:** ✅ Active - Maintains consistent height above ground level (AGL)
- **Accuracy:** ✅ Active - Flight paths account for hills, valleys, and elevation changes
- **Optimization:** ✅ Active - API calls are minimized - waypoints within 15 feet share elevation data

## Current Performance:
- **Elevation Caching**: Active - duplicate coordinates use cached data
- **Proximity Sharing**: Active - waypoints within 15 feet share elevation data
- **API Efficiency**: Typical spiral pattern uses 10-30 API calls depending on complexity
- **Real Data Examples**: 
  - Utah mountains: ~4,528 feet
  - NYC sea level: ~44 feet

## Production Deployment Checklist:
- [ ] Replace development API key with production key
- [ ] Set up environment variable for API key
- [ ] Remove hardcoded key from source code
- [ ] Test with production API limits
- [ ] Monitor API usage and costs 
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import json
import io
import logging
from spiral_logic import SpiralDesigner

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Initialize the spiral designer
designer = SpiralDesigner()

@app.route('/api/spiral-data', methods=['POST'])
def get_spiral_data():
    """
    Generate spiral visualization data
    Expected JSON payload:
    {
        "slices": 6,
        "N": 6,
        "r0": 1,
        "rHold": 50,
        "debugMode": false,
        "debugAngle": 0
    }
    """
    try:
        data = request.get_json()
        
        # Validate required parameters
        required_params = ['slices', 'N', 'r0', 'rHold']
        for param in required_params:
            if param not in data:
                return jsonify({'error': f'Missing required parameter: {param}'}), 400
        
        params = {
            'slices': int(data['slices']),
            'N': int(data['N']),
            'r0': float(data['r0']),
            'rHold': float(data['rHold'])
        }
        
        debug_mode = data.get('debugMode', False)
        debug_angle = float(data.get('debugAngle', 0))
        
        # Generate spiral data
        spiral_data = designer.generate_spiral_data(params, debug_mode, debug_angle)
        
        return jsonify(spiral_data)
    
    except Exception as e:
        logger.error(f"Error generating spiral data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/waypoints', methods=['POST'])
def get_waypoints():
    """
    Compute waypoints for console output
    Expected JSON payload:
    {
        "slices": 6,
        "N": 6,
        "r0": 1,
        "rHold": 50
    }
    """
    try:
        data = request.get_json()
        
        # Validate required parameters
        required_params = ['slices', 'N', 'r0', 'rHold']
        for param in required_params:
            if param not in data:
                return jsonify({'error': f'Missing required parameter: {param}'}), 400
        
        params = {
            'slices': int(data['slices']),
            'N': int(data['N']),
            'r0': float(data['r0']),
            'rHold': float(data['rHold'])
        }
        
        # Compute waypoints
        waypoints = designer.compute_waypoints(params)
        
        return jsonify({
            'waypoints': waypoints,
            'sliceCount': len(waypoints),
            'totalWaypoints': sum(len(slice_wp) for slice_wp in waypoints)
        })
    
    except Exception as e:
        logger.error(f"Error computing waypoints: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/csv', methods=['POST'])
def generate_csv():
    """
    Generate CSV file for Litchi mission (all slices combined)
    Expected JSON payload:
    {
        "slices": 6,
        "N": 6,
        "r0": 1,
        "rHold": 50,
        "center": "41.73218, -111.83979",
        "minHeight": 100,
        "maxHeight": 400,
        "debugMode": false,
        "debugAngle": 0
    }
    """
    try:
        data = request.get_json()
        
        # Validate required parameters
        required_params = ['slices', 'N', 'r0', 'rHold', 'center']
        for param in required_params:
            if param not in data:
                return jsonify({'error': f'Missing required parameter: {param}'}), 400
        
        params = {
            'slices': int(data['slices']),
            'N': int(data['N']),
            'r0': float(data['r0']),
            'rHold': float(data['rHold'])
        }
        
        center_str = data['center']
        min_height = float(data.get('minHeight', 100.0))
        max_height = float(data['maxHeight']) if data.get('maxHeight') else None
        debug_mode = data.get('debugMode', False)
        debug_angle = float(data.get('debugAngle', 0))
        
        # Generate CSV content
        csv_content = designer.generate_csv(params, center_str, min_height, max_height, debug_mode, debug_angle)
        
        # Create file-like object
        csv_buffer = io.StringIO(csv_content)
        csv_bytes = io.BytesIO(csv_buffer.getvalue().encode('utf-8'))
        
        return send_file(
            csv_bytes,
            mimetype='text/csv',
            as_attachment=True,
            download_name='litchi_spiral_mission_master.csv'
        )
    
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        logger.error(f"Error generating CSV: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/csv/battery/<int:battery_number>', methods=['POST'])
def generate_battery_csv(battery_number):
    """
    Generate CSV file for a specific battery/slice
    Expected JSON payload:
    {
        "slices": 6,
        "N": 6, 
        "r0": 1,
        "rHold": 50,
        "center": "41.73218, -111.83979",
        "minHeight": 100,
        "maxHeight": 400
    }
    """
    try:
        data = request.get_json()
        
        # Validate required parameters
        required_params = ['slices', 'N', 'r0', 'rHold', 'center']
        for param in required_params:
            if param not in data:
                return jsonify({'error': f'Missing required parameter: {param}'}), 400
        
        params = {
            'slices': int(data['slices']),
            'N': int(data['N']),
            'r0': float(data['r0']),
            'rHold': float(data['rHold'])
        }
        
        # Validate battery number
        if battery_number < 1 or battery_number > params['slices']:
            return jsonify({'error': f'Battery number must be between 1 and {params["slices"]}'}), 400
        
        center_str = data['center']
        min_height = float(data.get('minHeight', 100.0))
        max_height = float(data['maxHeight']) if data.get('maxHeight') else None
        
        # Generate CSV content for specific battery
        csv_content = designer.generate_battery_csv(params, center_str, battery_number - 1, min_height, max_height)  # Convert to 0-based index
        
        # Create file-like object
        csv_buffer = io.StringIO(csv_content)
        csv_bytes = io.BytesIO(csv_buffer.getvalue().encode('utf-8'))
        
        return send_file(
            csv_bytes,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'litchi_spiral_battery_{battery_number}.csv'
        )
    
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        logger.error(f"Error generating battery CSV: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'spiral-designer-api'})

@app.route('/api/validate-center', methods=['POST'])
def validate_center():
    """
    Validate center coordinates
    Expected JSON payload:
    {
        "center": "41.73218, -111.83979"
    }
    """
    try:
        data = request.get_json()
        center_str = data.get('center', '')
        
        parsed_center = designer.parse_center(center_str)
        
        if parsed_center:
            return jsonify({
                'valid': True,
                'parsed': parsed_center
            })
        else:
            return jsonify({
                'valid': False,
                'error': 'Invalid coordinate format'
            })
    
    except Exception as e:
        logger.error(f"Error validating center: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/elevation', methods=['POST'])
def get_elevation():
    """
    Get elevation for center coordinates
    Expected JSON payload:
    {
        "center": "41.73218, -111.83979"
    }
    """
    try:
        data = request.get_json()
        center_str = data.get('center', '')
        
        center = designer.parse_center(center_str)
        if not center:
            return jsonify({'error': 'Invalid coordinate format'}), 400
        
        elevation_feet = designer.get_elevation_feet(center['lat'], center['lon'])
        
        return jsonify({
            'elevation_feet': round(elevation_feet, 2),
            'elevation_meters': round(elevation_feet * 0.3048, 2),
            'coordinates': center
        })
    
    except Exception as e:
        logger.error(f"Error getting elevation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/optimize-spiral', methods=['POST'])
def optimize_spiral():
    """
    Optimize spiral parameters for given battery capacity
    Expected JSON payload:
    {
        "batteryMinutes": 20,
        "batteries": 3,
        "center": "41.73218, -111.83979"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required parameters
        required_params = ['batteryMinutes', 'batteries', 'center']
        for param in required_params:
            if param not in data:
                return jsonify({'error': f'Missing required parameter: {param}'}), 400
        
        battery_minutes = float(data['batteryMinutes'])
        batteries = int(data['batteries'])
        center_str = data['center']
        
        # Validate ranges
        if battery_minutes < 5 or battery_minutes > 60:
            return jsonify({'error': 'Battery minutes must be between 5 and 60'}), 400
        if batteries < 1 or batteries > 10:
            return jsonify({'error': 'Batteries must be between 1 and 10'}), 400
        
        # Parse center coordinates
        center = designer.parse_center(center_str)
        if not center:
            return jsonify({'error': 'Invalid center coordinates'}), 400
        
        # Optimize spiral parameters
        optimized_params = designer.optimize_spiral_for_battery(
            battery_minutes, 
            batteries, 
            center['lat'], 
            center['lon']
        )
        
        return jsonify({
            'optimized_params': optimized_params,
            'optimization_info': {
                'target_battery_minutes': battery_minutes,
                'estimated_time_minutes': optimized_params['estimated_time_minutes'],
                'battery_utilization_percent': optimized_params['battery_utilization'],
                'spiral_radius_feet': optimized_params['rHold'],
                'bounce_count': optimized_params['N']
            }
        })
    
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        logger.error(f"Error optimizing spiral: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Run the Flask app
    print("Starting Spiral Designer API...")
    print("Available endpoints:")
    print("  POST /api/spiral-data - Generate spiral visualization data")
    print("  POST /api/waypoints - Compute waypoints")
    print("  POST /api/csv - Generate master CSV file (all batteries)")
    print("  POST /api/csv/battery/<number> - Generate CSV file for specific battery")
    print("  POST /api/elevation - Get elevation for coordinates")
    print("  POST /api/optimize-spiral - Optimize spiral parameters for given battery capacity")
    print("  POST /api/validate-center - Validate center coordinates")
    print("  GET  /api/health - Health check")
    
    app.run(debug=True, host='0.0.0.0', port=5001) 
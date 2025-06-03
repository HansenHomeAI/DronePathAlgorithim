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
        debug_mode = data.get('debugMode', False)
        debug_angle = float(data.get('debugAngle', 0))
        
        # Generate CSV content
        csv_content = designer.generate_csv(params, center_str, debug_mode, debug_angle)
        
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
        "center": "41.73218, -111.83979"
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
        
        # Generate CSV content for specific battery
        csv_content = designer.generate_battery_csv(params, center_str, battery_number - 1)  # Convert to 0-based index
        
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

if __name__ == '__main__':
    # Run the Flask app
    print("Starting Spiral Designer API...")
    print("Available endpoints:")
    print("  POST /api/spiral-data - Generate spiral visualization data")
    print("  POST /api/waypoints - Compute waypoints")
    print("  POST /api/csv - Generate master CSV file (all batteries)")
    print("  POST /api/csv/battery/<number> - Generate CSV file for specific battery")
    print("  POST /api/validate-center - Validate center coordinates")
    print("  GET  /api/health - Health check")
    
    app.run(debug=True, host='0.0.0.0', port=5001) 
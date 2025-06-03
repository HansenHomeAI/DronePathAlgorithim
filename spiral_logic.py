import math
import json
import csv
import io
from typing import List, Dict, Tuple, Optional

class SpiralDesigner:
    """
    Bounded Spiral Designer - Python port of the JavaScript logic
    Generates drone flight patterns in spiral formations
    """
    
    # Constants
    MAX_ERR = 0.2
    EARTH_R = 6378137  # Earth radius in meters
    FT2M = 0.3048      # Feet to meters conversion
    
    def __init__(self):
        self.waypoint_cache = []
    
    def distance(self, a: Dict, b: Dict) -> float:
        """Calculate distance between two points"""
        return math.sqrt((a['x'] - b['x'])**2 + (a['y'] - b['y'])**2)
    
    def rotate_point(self, point: Dict, angle: float) -> Dict:
        """Rotate a point by given angle"""
        return {
            'x': point['x'] * math.cos(angle) - point['y'] * math.sin(angle),
            'y': point['x'] * math.sin(angle) + point['y'] * math.cos(angle)
        }
    
    def make_spiral(self, dphi: float, N: int, r0: float, r_hold: float, steps: int = 1200) -> List[Dict]:
        """
        Generate spiral points
        
        Args:
            dphi: Angular step size
            N: Number of bounces
            r0: Start radius
            r_hold: Hold radius
            steps: Number of steps in spiral
        """
        alpha = math.log(r_hold / r0) / (N * dphi)
        t_out = N * dphi
        t_hold = dphi
        t_total = 2 * t_out + t_hold
        
        spiral_points = []
        
        for i in range(steps):
            th = i * t_total / (steps - 1)
            
            # Calculate radius based on phase
            if th <= t_out:
                r = r0 * math.exp(alpha * th)
            elif th <= t_out + t_hold:
                r = r_hold
            else:
                r = r0 * math.exp(alpha * (t_total - th))
            
            # Calculate phase and phi
            phase = ((th / dphi) % 2 + 2) % 2
            phi = phase * dphi if phase <= 1 else (2 - phase) * dphi
            
            spiral_points.append({
                'x': r * math.cos(phi),
                'y': r * math.sin(phi)
            })
        
        return spiral_points
    
    def build_slice(self, slice_idx: int, params: Dict) -> List[Dict]:
        """
        Build waypoints for a single slice
        
        Args:
            slice_idx: Index of the slice
            params: Parameters dict with slices, N, r0, rHold
        """
        dphi = 2 * math.pi / params['slices']
        offset = math.pi / 2 + slice_idx * dphi
        
        # Generate spiral points
        spiral_pts = self.make_spiral(dphi, params['N'], params['r0'], params['rHold'])
        t_out = params['N'] * dphi
        t_hold = dphi
        t_total = 2 * t_out + t_hold
        
        waypoints = []
        
        def find_spiral_point(target_t: float, is_midpoint: bool = False, phase: str = 'unknown') -> Dict:
            """Find spiral point at given parameter t"""
            target_index = round(target_t * (len(spiral_pts) - 1) / t_total)
            clamped_index = max(0, min(len(spiral_pts) - 1, target_index))
            pt = spiral_pts[clamped_index]
            
            # Rotate point to match slice orientation
            rot_x = pt['x'] * math.cos(offset) - pt['y'] * math.sin(offset)
            rot_y = pt['x'] * math.sin(offset) + pt['y'] * math.cos(offset)
            
            # Dynamic curve radius calculation
            distance_from_center = math.sqrt(rot_x**2 + rot_y**2)
            
            if is_midpoint:
                # Midpoint curve equation: larger curves for smooth transitions
                base_curve = 50
                scale_factor = 1.2
                max_curve = 1500
                curve_radius = min(max_curve, base_curve + (distance_from_center * scale_factor))
            else:
                # Non-midpoint curve equation: smaller, conservative curves
                base_curve = 20
                scale_factor = 0.05
                max_curve = 80
                curve_radius = min(max_curve, base_curve + (distance_from_center * scale_factor))
            
            curve_radius = round(curve_radius * 10) / 10  # Round to 1 decimal
            
            return {
                'x': rot_x,
                'y': rot_y,
                'curve': curve_radius,
                'phase': phase,
                't': target_t,
                'id': f"{phase}_{target_t:.3f}"
            }
        
        # PHASE 1: Outward spiral
        waypoints.append(find_spiral_point(0, False, 'outbound_start'))
        
        for bounce in range(1, params['N'] + 1):
            # Add midpoint before bounce
            t_mid = (bounce - 0.5) * dphi
            waypoints.append(find_spiral_point(t_mid, True, f'outbound_mid_{bounce}'))
            
            # Add bounce point
            t_bounce = bounce * dphi
            waypoints.append(find_spiral_point(t_bounce, False, f'outbound_bounce_{bounce}'))
        
        # PHASE 2: Hold phase
        t_mid_hold = t_out + t_hold / 2
        t_end_hold = t_out + t_hold
        
        waypoints.append(find_spiral_point(t_mid_hold, True, 'hold_mid'))
        waypoints.append(find_spiral_point(t_end_hold, False, 'hold_end'))
        
        # PHASE 3: Inbound spiral
        t_first_inbound_mid = t_end_hold + 0.5 * dphi
        waypoints.append(find_spiral_point(t_first_inbound_mid, True, 'inbound_mid_0'))
        
        for bounce in range(1, params['N'] + 1):
            # Add bounce point
            t_bounce = t_end_hold + bounce * dphi
            waypoints.append(find_spiral_point(t_bounce, False, f'inbound_bounce_{bounce}'))
            
            # Add midpoint after bounce (except after final bounce)
            if bounce < params['N']:
                t_mid = t_end_hold + (bounce + 0.5) * dphi
                waypoints.append(find_spiral_point(t_mid, True, f'inbound_mid_{bounce}'))
        
        return waypoints
    
    def compute_waypoints(self, params: Dict) -> List[List[Dict]]:
        """Compute waypoints for all slices"""
        self.waypoint_cache = []
        for i in range(params['slices']):
            self.waypoint_cache.append(self.build_slice(i, params))
        return self.waypoint_cache
    
    def parse_center(self, txt: str) -> Optional[Dict]:
        """Parse center coordinates from various formats"""
        import re
        
        txt = txt.strip()
        
        # Handle formats like "41.73218° N, 111.83979° W"
        degree_match = re.search(r'(\d+\.?\d*)\s*°?\s*([NS])\s*,\s*(\d+\.?\d*)\s*°?\s*([EW])', txt, re.IGNORECASE)
        if degree_match:
            lat = float(degree_match.group(1))
            lon = float(degree_match.group(3))
            
            if degree_match.group(2).upper() == 'S':
                lat = -lat
            if degree_match.group(4).upper() == 'W':
                lon = -lon
            
            return {'lat': lat, 'lon': lon}
        
        # Handle simple decimal format like "41.73218, -111.83979"
        decimal_match = re.search(r'([-+]?\d+\.?\d*)\s*,\s*([-+]?\d+\.?\d*)', txt)
        if decimal_match:
            return {
                'lat': float(decimal_match.group(1)),
                'lon': float(decimal_match.group(2))
            }
        
        return None
    
    def xy_to_lat_lon(self, x_ft: float, y_ft: float, lat0: float, lon0: float) -> Dict:
        """Convert X,Y coordinates to lat/lon"""
        x_m = x_ft * self.FT2M
        y_m = y_ft * self.FT2M
        
        d_lat = y_m / self.EARTH_R
        d_lon = x_m / (self.EARTH_R * math.cos(lat0 * math.pi / 180))
        
        return {
            'lat': lat0 + d_lat * 180 / math.pi,
            'lon': lon0 + d_lon * 180 / math.pi
        }
    
    def generate_spiral_data(self, params: Dict, debug_mode: bool = False, debug_angle: float = 0) -> Dict:
        """
        Generate spiral visualization data
        
        Args:
            params: Parameters dict
            debug_mode: Whether to show single slice
            debug_angle: Angle for debug slice (in degrees)
        """
        dphi = 2 * math.pi / params['slices']
        raw_spiral = self.make_spiral(dphi, params['N'], params['r0'], params['rHold'])
        
        traces = []
        hue0, hue1 = 220, 300
        offset = math.pi / 2
        
        if debug_mode:
            # Debug mode: single slice
            debug_angle_rad = debug_angle * math.pi / 180
            angle = math.pi / 2 + debug_angle_rad
            c, s = math.cos(angle), math.sin(angle)
            
            # Spiral trace
            spiral_x = [pt['x'] * c - pt['y'] * s for pt in raw_spiral]
            spiral_y = [pt['x'] * s + pt['y'] * c for pt in raw_spiral]
            
            traces.append({
                'x': spiral_x,
                'y': spiral_y,
                'mode': 'lines',
                'line': {'color': '#0a84ff', 'width': 3},
                'name': 'Debug Slice'
            })
            
            # Radius line
            traces.append({
                'x': [0, params['rHold'] * math.cos(angle)],
                'y': [0, params['rHold'] * math.sin(angle)],
                'mode': 'lines',
                'line': {'color': '#ff9500', 'width': 2, 'dash': 'dot'},
                'name': 'Radius'
            })
        else:
            # Full pattern mode
            for k in range(params['slices']):
                angle = offset + k * dphi
                c, s = math.cos(angle), math.sin(angle)
                
                # Spiral trace
                spiral_x = [pt['x'] * c - pt['y'] * s for pt in raw_spiral]
                spiral_y = [pt['x'] * s + pt['y'] * c for pt in raw_spiral]
                
                hue = hue0 + (hue1 - hue0) * (k / (params['slices'] - 1) if params['slices'] > 1 else 0)
                
                traces.append({
                    'x': spiral_x,
                    'y': spiral_y,
                    'mode': 'lines',
                    'line': {'color': f'hsl({hue} 80% 55%)', 'width': 2}
                })
                
                # Radius line
                traces.append({
                    'x': [0, params['rHold'] * math.cos(angle)],
                    'y': [0, params['rHold'] * math.sin(angle)],
                    'mode': 'lines',
                    'line': {'color': '#ff9500', 'width': 2, 'dash': 'dot'}
                })
        
        return {'traces': traces}
    
    def generate_csv(self, params: Dict, center_str: str, debug_mode: bool = False, debug_angle: float = 0) -> str:
        """Generate CSV for Litchi mission"""
        center = self.parse_center(center_str)
        if not center:
            raise ValueError("Invalid center coordinates")
        
        # Generate waypoints using the same algorithm as the designer
        spiral_path = []
        
        if debug_mode:
            # Debug mode: single slice
            debug_angle_rad = debug_angle * math.pi / 180
            slice_index = round(debug_angle_rad / (2 * math.pi / params['slices'])) % params['slices']
            waypoints = self.compute_waypoints(params)
            
            if waypoints:
                spiral_path = waypoints[slice_index] if slice_index < len(waypoints) else waypoints[0]
                
                # Rotate to exact debug angle
                actual_slice_angle = slice_index * (2 * math.pi / params['slices'])
                rotation_diff = debug_angle_rad - actual_slice_angle
                
                rotated_path = []
                for wp in spiral_path:
                    rotated_x = wp['x'] * math.cos(rotation_diff) - wp['y'] * math.sin(rotation_diff)
                    rotated_y = wp['x'] * math.sin(rotation_diff) + wp['y'] * math.cos(rotation_diff)
                    
                    rotated_wp = wp.copy()
                    rotated_wp['x'] = rotated_x
                    rotated_wp['y'] = rotated_y
                    rotated_path.append(rotated_wp)
                
                spiral_path = rotated_path
        else:
            # Full pattern mode
            waypoints = self.compute_waypoints(params)
            spiral_path = []
            for slice_waypoints in waypoints:
                spiral_path.extend(slice_waypoints)
        
        # Ensure minimum curve radius
        for wp in spiral_path:
            wp['curve'] = max(wp['curve'], 15)  # Minimum 15ft curve radius
        
        # Generate CSV content
        header = "latitude,longitude,altitude(ft),heading(deg),curvesize(ft),rotationdir,gimbalmode,gimbalpitchangle,altitudemode,speed(m/s),poi_latitude,poi_longitude,poi_altitude(ft),poi_altitudemode,photo_timeinterval,photo_distinterval"
        rows = [header]
        
        for i, wp in enumerate(spiral_path):
            # Convert to lat/lon
            coords = self.xy_to_lat_lon(wp['x'], wp['y'], center['lat'], center['lon'])
            latitude = round(coords['lat'] * 100000) / 100000
            longitude = round(coords['lon'] * 100000) / 100000
            
            # Calculate altitude based on distance from center
            dist_from_center = math.sqrt(wp['x']**2 + wp['y']**2)
            base_altitude = 70
            altitude = round((base_altitude + (dist_from_center * 0.8)) * 100) / 100
            
            # Calculate heading to next waypoint
            heading = 0
            if i < len(spiral_path) - 1:
                next_wp = spiral_path[i + 1]
                dx = next_wp['x'] - wp['x']
                dy = next_wp['y'] - wp['y']
                heading = round(((math.atan2(dx, dy) * 180 / math.pi) + 360) % 360)
            
            # Use curve radius from spiral calculation
            curve_size_meters = round((wp['curve'] * self.FT2M) * 100) / 100
            
            # Calculate gimbal pitch based on waypoint position
            progress = i / (len(spiral_path) - 1) if len(spiral_path) > 1 else 0
            gimbal_pitch = round(-35 + 14 * math.sin(progress * math.pi))
            
            # Create row
            row = [
                latitude,
                longitude,
                altitude,
                heading,
                curve_size_meters,
                0,                      # rotationdir
                2,                      # gimbalmode
                gimbal_pitch,           # gimbalpitchangle
                0,                      # altitudemode
                8.85,                   # speed(m/s)
                center['lat'],          # poi_latitude
                center['lon'],          # poi_longitude
                0,                      # poi_altitude
                0,                      # poi_altitudemode
                0 if i == 0 else 2.8,  # photo_timeinterval
                0                       # photo_distinterval
            ]
            
            rows.append(','.join(map(str, row)))
        
        return '\n'.join(rows)

    def generate_battery_csv(self, params: Dict, center_str: str, battery_index: int) -> str:
        """Generate CSV for a specific battery/slice (0-based index)"""
        center = self.parse_center(center_str)
        if not center:
            raise ValueError("Invalid center coordinates")
            
        # Validate battery index
        if battery_index < 0 or battery_index >= params['slices']:
            raise ValueError(f"Battery index must be between 0 and {params['slices'] - 1}")
        
        # Generate waypoints for all slices, then extract the specific one
        all_waypoints = self.compute_waypoints(params)
        spiral_path = all_waypoints[battery_index]
        
        # Ensure minimum curve radius
        for wp in spiral_path:
            wp['curve'] = max(wp['curve'], 15)  # Minimum 15ft curve radius
        
        # Generate CSV content
        header = "latitude,longitude,altitude(ft),heading(deg),curvesize(ft),rotationdir,gimbalmode,gimbalpitchangle,altitudemode,speed(m/s),poi_latitude,poi_longitude,poi_altitude(ft),poi_altitudemode,photo_timeinterval,photo_distinterval"
        rows = [header]
        
        for i, wp in enumerate(spiral_path):
            # Convert to lat/lon
            coords = self.xy_to_lat_lon(wp['x'], wp['y'], center['lat'], center['lon'])
            latitude = round(coords['lat'] * 100000) / 100000
            longitude = round(coords['lon'] * 100000) / 100000
            
            # Calculate altitude based on distance from center
            dist_from_center = math.sqrt(wp['x']**2 + wp['y']**2)
            base_altitude = 70
            altitude = round((base_altitude + (dist_from_center * 0.8)) * 100) / 100
            
            # Calculate heading to next waypoint
            heading = 0
            if i < len(spiral_path) - 1:
                next_wp = spiral_path[i + 1]
                dx = next_wp['x'] - wp['x']
                dy = next_wp['y'] - wp['y']
                heading = round(((math.atan2(dx, dy) * 180 / math.pi) + 360) % 360)
            
            # Use curve radius from spiral calculation
            curve_size_meters = round((wp['curve'] * self.FT2M) * 100) / 100
            
            # Calculate gimbal pitch based on waypoint position
            progress = i / (len(spiral_path) - 1) if len(spiral_path) > 1 else 0
            gimbal_pitch = round(-35 + 14 * math.sin(progress * math.pi))
            
            # Create row
            row = [
                latitude,
                longitude,
                altitude,
                heading,
                curve_size_meters,
                0,                      # rotationdir
                2,                      # gimbalmode
                gimbal_pitch,           # gimbalpitchangle
                0,                      # altitudemode
                8.85,                   # speed(m/s)
                center['lat'],          # poi_latitude
                center['lon'],          # poi_longitude
                0,                      # poi_altitude
                0,                      # poi_altitudemode
                0 if i == 0 else 2.8,  # photo_timeinterval
                0                       # photo_distinterval
            ]
            
            rows.append(','.join(map(str, row)))
        
        return '\n'.join(rows)

# Example usage and testing
if __name__ == "__main__":
    designer = SpiralDesigner()
    
    # Test parameters
    test_params = {
        'slices': 6,
        'N': 6,
        'r0': 1,
        'rHold': 50
    }
    
    # Test waypoint generation
    waypoints = designer.compute_waypoints(test_params)
    print(f"Generated {len(waypoints)} slices with waypoints")
    
    # Test CSV generation
    try:
        csv_content = designer.generate_csv(
            test_params, 
            "41.73218, -111.83979",
            debug_mode=False
        )
        print(f"Generated CSV with {len(csv_content.split(chr(10))) - 1} waypoints")
    except Exception as e:
        print(f"CSV generation error: {e}") 
import math
import json
import csv
import io
import os
import requests
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
        self.elevation_cache = {}  # Cache for elevation data
        
        # DEVELOPMENT API KEY - DO NOT DELETE UNTIL PRODUCTION DEPLOYMENT
        # This is a development/testing API key, replace with environment variable for production
        dev_api_key = "AIzaSyDkdnE1weVG38PSUO5CWFneFjH16SPYZHU"
        
        # Try environment variable first, fallback to development key
        self.api_key = os.environ.get("GOOGLE_MAPS_API_KEY", dev_api_key)
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two lat/lon points in meters"""
        R = 6371000.0  # Earth radius in meters
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = (math.sin(dLat/2)**2 +
             math.cos(math.radians(lat1)) *
             math.cos(math.radians(lat2)) *
             math.sin(dLon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def get_elevation_feet(self, lat: float, lon: float) -> float:
        """Get elevation in feet for a single coordinate using Google Maps API"""
        # Check cache first
        cache_key = f"{lat:.6f},{lon:.6f}"
        if cache_key in self.elevation_cache:
            return self.elevation_cache[cache_key]
        
        if not self.api_key:
            # Return a default elevation if no API key
            print("Warning: No Google Maps API key available, using default elevation")
            return 4500.0  # Default elevation in feet
        
        try:
            url = f"https://maps.googleapis.com/maps/api/elevation/json?locations={lat},{lon}&key={self.api_key}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                raise ValueError(f"Elevation HTTP error {response.status_code}")
            
            data = response.json()
            if data["status"] != "OK" or not data["results"]:
                print(f"Google Elevation API error: {data.get('status', 'Unknown error')}")
                # Use a more reasonable default for most locations
                return 1000.0  # Default to 1000ft if API fails
            
            elevation_meters = data["results"][0]["elevation"]
            elevation_feet = elevation_meters * 3.28084
            
            # Cache the result
            self.elevation_cache[cache_key] = elevation_feet
            print(f"Elevation fetched: {lat:.5f},{lon:.5f} = {elevation_feet:.1f} ft")
            return elevation_feet
            
        except Exception as e:
            print(f"Elevation API error for {lat},{lon}: {str(e)}")
            # Return reasonable default elevation on error
            return 1000.0
    
    def get_elevations_feet_optimized(self, locations: List[Tuple[float, float]]) -> List[float]:
        """
        Get elevations for multiple locations with 15-foot optimization.
        If two waypoints are within 15 feet of each other, share elevation data.
        """
        if not locations:
            return []
        
        elevations = []
        processed_locations = []
        
        for i, (lat, lon) in enumerate(locations):
            # Check if we can reuse elevation from a nearby processed location
            reused_elevation = None
            
            for j, (prev_lat, prev_lon, prev_elev) in enumerate(processed_locations):
                distance_ft = self.haversine_distance(lat, lon, prev_lat, prev_lon) * 3.28084
                if distance_ft <= 15.0:  # Within 15 feet
                    reused_elevation = prev_elev
                    break
            
            if reused_elevation is not None:
                elevations.append(reused_elevation)
                processed_locations.append((lat, lon, reused_elevation))
            else:
                # Need to fetch new elevation
                elevation = self.get_elevation_feet(lat, lon)
                elevations.append(elevation)
                processed_locations.append((lat, lon, elevation))
        
        return elevations
    
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
    
    def generate_csv(self, params: Dict, center_str: str, min_height: float = 100.0, max_height: float = None, debug_mode: bool = False, debug_angle: float = 0) -> str:
        """Generate CSV for Litchi mission with elevation-aware altitudes"""
        center = self.parse_center(center_str)
        if not center:
            raise ValueError("Invalid center coordinates")
        
        # Get takeoff elevation for reference
        takeoff_elevation_feet = self.get_elevation_feet(center['lat'], center['lon'])
        
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
        
        # Convert waypoints to lat/lon and get optimized elevations
        locations = []
        for wp in spiral_path:
            coords = self.xy_to_lat_lon(wp['x'], wp['y'], center['lat'], center['lon'])
            locations.append((coords['lat'], coords['lon']))
        
        # Get elevations with optimization
        ground_elevations = self.get_elevations_feet_optimized(locations)
        
        # Generate CSV content
        header = "latitude,longitude,altitude(ft),heading(deg),curvesize(ft),rotationdir,gimbalmode,gimbalpitchangle,altitudemode,speed(m/s),poi_latitude,poi_longitude,poi_altitude(ft),poi_altitudemode,photo_timeinterval,photo_distinterval"
        rows = [header]
        
        # Track first waypoint distance for relative altitude calculation
        first_waypoint_distance = 0
        
        for i, wp in enumerate(spiral_path):
            # Convert to lat/lon
            coords = self.xy_to_lat_lon(wp['x'], wp['y'], center['lat'], center['lon'])
            latitude = round(coords['lat'] * 100000) / 100000
            longitude = round(coords['lon'] * 100000) / 100000
            
            # Calculate elevation-aware altitude
            ground_elevation = ground_elevations[i]
            local_ground_offset = ground_elevation - takeoff_elevation_feet
            if local_ground_offset < 0:
                local_ground_offset = 0
            
            # Calculate desired AGL based on distance from center
            dist_from_center = math.sqrt(wp['x']**2 + wp['y']**2)
            
            # NEW LOGIC: First waypoint starts at min_height, subsequent waypoints increase relative to first
            if i == 0:
                # First waypoint starts at min_height regardless of distance from center
                first_waypoint_distance = dist_from_center
                desired_agl = min_height
            else:
                # Subsequent waypoints increase at 0.5ft per foot of additional distance from first waypoint
                additional_distance = dist_from_center - first_waypoint_distance
                if additional_distance < 0:
                    additional_distance = 0  # In case we get closer to center
                agl_increment = additional_distance * 0.5  # Reduced from 0.8 to 0.5 feet per foot
                desired_agl = min_height + agl_increment
            
            # Calculate final altitude
            final_altitude = local_ground_offset + desired_agl
            
            # Apply max height constraint if specified
            if max_height is not None:
                adjusted_max_height = max_height - takeoff_elevation_feet
                current_agl = final_altitude - ground_elevation
                if current_agl > adjusted_max_height:
                    final_altitude = ground_elevation + adjusted_max_height
            
            altitude = round(final_altitude * 100) / 100
            
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

    def generate_battery_csv(self, params: Dict, center_str: str, battery_index: int, min_height: float = 100.0, max_height: float = None) -> str:
        """Generate CSV for a specific battery/slice (0-based index) with elevation-aware altitudes"""
        center = self.parse_center(center_str)
        if not center:
            raise ValueError("Invalid center coordinates")
            
        # Validate battery index
        if battery_index < 0 or battery_index >= params['slices']:
            raise ValueError(f"Battery index must be between 0 and {params['slices'] - 1}")
        
        # Get takeoff elevation for reference
        takeoff_elevation_feet = self.get_elevation_feet(center['lat'], center['lon'])
        
        # Generate waypoints for all slices, then extract the specific one
        all_waypoints = self.compute_waypoints(params)
        spiral_path = all_waypoints[battery_index]
        
        # Ensure minimum curve radius
        for wp in spiral_path:
            wp['curve'] = max(wp['curve'], 15)  # Minimum 15ft curve radius
        
        # Convert waypoints to lat/lon and get optimized elevations
        locations = []
        for wp in spiral_path:
            coords = self.xy_to_lat_lon(wp['x'], wp['y'], center['lat'], center['lon'])
            locations.append((coords['lat'], coords['lon']))
        
        # Get elevations with optimization
        ground_elevations = self.get_elevations_feet_optimized(locations)
        
        # Generate CSV content
        header = "latitude,longitude,altitude(ft),heading(deg),curvesize(ft),rotationdir,gimbalmode,gimbalpitchangle,altitudemode,speed(m/s),poi_latitude,poi_longitude,poi_altitude(ft),poi_altitudemode,photo_timeinterval,photo_distinterval"
        rows = [header]
        
        # Track first waypoint distance for relative altitude calculation
        first_waypoint_distance = 0
        
        for i, wp in enumerate(spiral_path):
            # Convert to lat/lon
            coords = self.xy_to_lat_lon(wp['x'], wp['y'], center['lat'], center['lon'])
            latitude = round(coords['lat'] * 100000) / 100000
            longitude = round(coords['lon'] * 100000) / 100000
            
            # Calculate elevation-aware altitude
            ground_elevation = ground_elevations[i]
            local_ground_offset = ground_elevation - takeoff_elevation_feet
            if local_ground_offset < 0:
                local_ground_offset = 0
            
            # Calculate desired AGL based on distance from center
            dist_from_center = math.sqrt(wp['x']**2 + wp['y']**2)
            
            # NEW LOGIC: First waypoint starts at min_height, subsequent waypoints increase relative to first
            if i == 0:
                # First waypoint starts at min_height regardless of distance from center
                first_waypoint_distance = dist_from_center
                desired_agl = min_height
            else:
                # Subsequent waypoints increase at 0.5ft per foot of additional distance from first waypoint
                additional_distance = dist_from_center - first_waypoint_distance
                if additional_distance < 0:
                    additional_distance = 0  # In case we get closer to center
                agl_increment = additional_distance * 0.5  # Reduced from 0.8 to 0.5 feet per foot
                desired_agl = min_height + agl_increment
            
            # Calculate final altitude
            final_altitude = local_ground_offset + desired_agl
            
            # Apply max height constraint if specified
            if max_height is not None:
                adjusted_max_height = max_height - takeoff_elevation_feet
                current_agl = final_altitude - ground_elevation
                if current_agl > adjusted_max_height:
                    final_altitude = ground_elevation + adjusted_max_height
            
            altitude = round(final_altitude * 100) / 100
            
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

    def estimate_flight_time_minutes(self, params: Dict, center_lat: float, center_lon: float) -> float:
        """
        Estimate flight time in minutes for a SINGLE battery/slice
        Each battery represents one separate flight, not combined mission time
        """
        # Flight parameters
        speed_mph = 19.8
        speed_mps = speed_mph * 0.44704  # Convert to m/s
        vertical_speed_mps = 5.0  # Vertical speed in m/s
        hover_time = 3  # Hover time per waypoint
        accel_time = 2  # Acceleration time per waypoint
        
        # Get waypoints for all slices, but we only need ONE slice for timing
        all_waypoints = self.compute_waypoints(params)
        
        if not all_waypoints:
            return 0.0
        
        # Calculate time for ONE slice (since each battery flies one slice separately)
        slice_waypoints = all_waypoints[0]  # Use first slice as representative
        
        if not slice_waypoints:
            return 0.0
            
        slice_time = 0.0
        
        # Start at takeoff location (center coordinates)
        prev_lat, prev_lon = center_lat, center_lon
        min_height = 100.0  # Use the same default min height as other methods
        prev_altitude = min_height  # Start at min height
        
        # Time to ascend to first waypoint
        first_wp = slice_waypoints[0]
        ascend_time = (min_height * self.FT2M) / vertical_speed_mps
        slice_time += ascend_time
        
        # Track first waypoint distance for relative altitude calculation
        first_waypoint_distance = 0
        
        # Process each waypoint in the slice
        for i, wp in enumerate(slice_waypoints):
            # Convert waypoint coordinates to lat/lon
            coords = self.xy_to_lat_lon(wp['x'], wp['y'], center_lat, center_lon)
            
            # Calculate altitude using new relative logic
            dist_from_center = math.sqrt(wp['x']**2 + wp['y']**2)
            
            if i == 0:
                # First waypoint starts at min_height regardless of distance from center
                first_waypoint_distance = dist_from_center
                wp_altitude = min_height
            else:
                # Subsequent waypoints increase at 0.5ft per foot of additional distance from first waypoint
                additional_distance = dist_from_center - first_waypoint_distance
                if additional_distance < 0:
                    additional_distance = 0  # In case we get closer to center
                agl_increment = additional_distance * 0.5  # 0.5 feet per foot
                wp_altitude = min_height + agl_increment
            
            # Calculate horizontal distance from previous position
            horizontal_dist_m = self.haversine_distance(prev_lat, prev_lon, coords['lat'], coords['lon'])
            
            # Calculate altitude difference
            altitude_diff_ft = abs(wp_altitude - prev_altitude)
            altitude_diff_m = altitude_diff_ft * self.FT2M
            
            # Time calculations
            horizontal_time = horizontal_dist_m / speed_mps
            vertical_time = altitude_diff_m / vertical_speed_mps
            segment_time = horizontal_time + vertical_time + hover_time + accel_time
            
            slice_time += segment_time
            
            # Update previous position
            prev_lat, prev_lon = coords['lat'], coords['lon']
            prev_altitude = wp_altitude
        
        # Time to return home from last waypoint
        last_coords = self.xy_to_lat_lon(slice_waypoints[-1]['x'], slice_waypoints[-1]['y'], center_lat, center_lon)
        return_dist_m = self.haversine_distance(last_coords['lat'], last_coords['lon'], center_lat, center_lon)
        return_altitude_diff_m = (prev_altitude - min_height) * self.FT2M  # Return to starting altitude
        
        return_time = (return_dist_m / speed_mps) + (abs(return_altitude_diff_m) / vertical_speed_mps) + accel_time
        slice_time += return_time
        
        # Time to descend and land
        descent_time = (min_height * self.FT2M) / vertical_speed_mps
        slice_time += descent_time
        
        return slice_time / 60.0  # Convert to minutes
    
    def optimize_spiral_for_battery(self, target_battery_minutes: float, num_batteries: int, center_lat: float, center_lon: float) -> Dict:
        """
        Use balanced optimization to scale both radius and bounces with battery capacity
        Creates proportional scaling for optimal coverage quality
        """
        # Parameter constraints
        min_r0, max_r0 = 50.0, 500.0  # Start radius range
        min_rHold, max_rHold = 200.0, 4000.0  # Hold radius range  
        min_N, max_N = 3, 12  # Bounce count range
        
        # BALANCED SCALING: Scale bounce count with battery duration first
        # 10 min → 5 bounces, 20 min → 8 bounces, 30 min → 10 bounces
        if target_battery_minutes <= 12:
            target_bounces = 5
        elif target_battery_minutes <= 18:
            target_bounces = 6
        elif target_battery_minutes <= 25:
            target_bounces = 8
        elif target_battery_minutes <= 35:
            target_bounces = 10
        else:
            target_bounces = 12
        
        # Clamp to valid range
        target_bounces = max(min_N, min(max_N, target_bounces))
        
        # Start with balanced base parameters
        base_params = {
            'slices': num_batteries,
            'N': target_bounces,  # Use scaled bounce count
            'r0': 150.0  # Standard start radius
        }
        
        print(f"Optimizing for {target_battery_minutes}min battery: targeting {target_bounces} bounces")
        
        # First check if minimum parameters fit
        test_params = base_params.copy()
        test_params['rHold'] = min_rHold
        
        try:
            min_time = self.estimate_flight_time_minutes(test_params, center_lat, center_lon)
            if min_time > target_battery_minutes:
                # Even minimum doesn't fit - reduce bounces and try again
                reduced_bounces = max(min_N, target_bounces - 2)
                print(f"Minimum spiral too large, reducing bounces from {target_bounces} to {reduced_bounces}")
                base_params['N'] = reduced_bounces
                target_bounces = reduced_bounces
                
                test_params = base_params.copy()
                test_params['rHold'] = min_rHold
                min_time = self.estimate_flight_time_minutes(test_params, center_lat, center_lon)
                
                if min_time > target_battery_minutes:
                    # Still too big - return absolute minimum
                    return {
                        'slices': num_batteries,
                        'N': min_N,
                        'r0': 100.0,
                        'rHold': min_rHold,
                        'estimated_time_minutes': min_time,
                        'battery_utilization': round((min_time / target_battery_minutes) * 100, 1)
                    }
        except Exception as e:
            print(f"Error testing minimum parameters: {e}")
        
        # Binary search on hold radius with FIXED bounce count
        best_params = None
        best_time = 0.0
        
        low, high = min_rHold, max_rHold
        tolerance = 10.0  # 10ft tolerance
        max_iterations = 20
        iterations = 0
        
        while high - low > tolerance and iterations < max_iterations:
            iterations += 1
            mid_rHold = (low + high) / 2
            
            # Test parameters with current hold radius and FIXED bounce count
            test_params = base_params.copy()
            test_params['rHold'] = mid_rHold
            
            try:
                estimated_time = self.estimate_flight_time_minutes(test_params, center_lat, center_lon)
                
                # Add 5% safety margin
                if estimated_time <= target_battery_minutes * 0.95:
                    # This size fits comfortably, try larger
                    best_params = test_params.copy()
                    best_time = estimated_time
                    low = mid_rHold
                else:
                    # Too big, try smaller
                    high = mid_rHold
                    
            except Exception as e:
                print(f"Error estimating time for rHold={mid_rHold}: {e}")
                high = mid_rHold
        
        # Try to add ONE more bounce if we have significant headroom (< 85% usage)
        if best_params and best_time < target_battery_minutes * 0.85 and target_bounces < max_N:
            test_params = best_params.copy()
            test_params['N'] = target_bounces + 1
            
            try:
                estimated_time = self.estimate_flight_time_minutes(test_params, center_lat, center_lon)
                if estimated_time <= target_battery_minutes * 0.95:
                    print(f"Adding bonus bounce: {target_bounces} → {target_bounces + 1}")
                    best_params = test_params.copy()
                    best_time = estimated_time
            except:
                pass  # Keep original if bonus bounce fails
        
        # Final safety check
        if not best_params:
            best_params = {
                'slices': num_batteries,
                'N': target_bounces,
                'r0': 150.0,
                'rHold': min_rHold
            }
            try:
                best_time = self.estimate_flight_time_minutes(best_params, center_lat, center_lon)
            except:
                best_time = target_battery_minutes * 1.2
        
        # Add timing info to results
        best_params['estimated_time_minutes'] = round(best_time, 2)
        best_params['battery_utilization'] = round((best_time / target_battery_minutes) * 100, 1)
        
        print(f"Final optimization: {best_params['N']} bounces, {best_params['rHold']:.0f}ft radius, {best_time:.1f}min ({best_params['battery_utilization']}%)")
        
        return best_params

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
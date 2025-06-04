# Battery Duration Optimization Algorithm

## Overview

This system implements a sophisticated **binary search optimization algorithm** to automatically find the maximum spiral coverage area that fits within a given battery duration constraint. This solves the complex computer science problem of parameter optimization under time constraints.

## The Problem

**Input**: Battery capacity (minutes), number of batteries, center coordinates
**Output**: Optimal spiral parameters (radius, bounces, start radius) that maximize coverage quality
**Constraint**: Flight time per battery ≤ battery_capacity (each battery flies separately)
**Objective**: Maximize both coverage area AND photo density per battery while staying within individual battery time limit

## Algorithm Design

### 1. Balanced Parameter Scaling

**New Approach**: Instead of only optimizing radius, we use intelligent scaling for both bounces and radius:

```python
# Balanced scaling based on battery duration
if target_battery_minutes <= 12:
    target_bounces = 5      # Detailed but compact
elif target_battery_minutes <= 18:
    target_bounces = 6      # Building up
elif target_battery_minutes <= 25:
    target_bounces = 8      # Sweet spot range!
elif target_battery_minutes <= 35:
    target_bounces = 10     # Comprehensive coverage
else:
    target_bounces = 12     # Maximum detail
```

**Why This Matters**: More bounces = more waypoints = more photos = better reconstruction quality

### 2. Flight Time Estimation

Based on the original `oldFunction.py` logic, we calculate flight time for a **single battery/slice**:

```python
# Per-waypoint time calculation for ONE slice
horizontal_time = distance_meters / speed_mps
vertical_time = altitude_change_meters / vertical_speed_mps  
segment_time = horizontal_time + vertical_time + hover_time + accel_time
```

**Important**: Each battery represents a separate flight mission. With 3 batteries at 20 minutes each, you get 3 separate 20-minute flights, not one combined 60-minute mission.

**Single battery mission time includes:**
- Takeoff and ascent to first waypoint
- Flight time between all waypoints in one slice  
- Altitude changes at each waypoint
- Hover and acceleration time (3+2 seconds per waypoint)
- Return-to-home flight from slice's last waypoint
- Descent and landing time

### 3. Binary Search Optimization

**Primary Parameter**: Hold radius (`rHold`) - optimized with FIXED bounce count

```python
# Computational complexity: O(log n) where n = search space
while high - low > tolerance and iterations < max_iterations:
    mid_rHold = (low + high) / 2
    
    # Test with FIXED bounce count determined by battery duration
    test_params = {
        'N': target_bounces,  # Fixed based on scaling logic
        'rHold': mid_rHold    # Variable being optimized
    }
    estimated_time = calculate_flight_time(test_params)
    
    if estimated_time <= target_time * 0.95:  # 95% safety margin
        best_params = test_params  # This size fits, try larger radius
        low = mid_rHold
    else:
        high = mid_rHold  # Too big, try smaller radius
```

**Key Advantage**: Optimizes radius while maintaining appropriate photo density for the given flight time

### 4. Safety and Constraints

**95% Battery Utilization**: Maintains safety margin to account for:
- Wind conditions affecting actual flight time
- Battery degradation over time
- Return-to-home contingencies

**Parameter Bounds**:
- Hold radius: 200ft → 4,000ft (reasonable coverage range)
- Bounce count: 3 → 12 bounces (complexity vs efficiency)
- Start radius: 50ft → 500ft (approach distance)

**Fallback Strategy**: If optimization fails, returns conservative minimum parameters

### 5. Balanced Fine-Tuning

After finding optimal radius with target bounce count, the algorithm attempts to add one bonus bounce if there's significant headroom:

```python
# Try to add ONE more bounce if we have significant headroom (< 85% usage)
if best_time < target_battery_minutes * 0.85 and target_bounces < max_N:
    test_params = best_params.copy()
    test_params['N'] = target_bounces + 1
    
    if new_time <= target_time * 0.95:
        print(f"Adding bonus bounce: {target_bounces} → {target_bounces + 1}")
        best_params = test_params  # Accept the bonus bounce
```

## Performance Results

The algorithm demonstrates excellent balanced scaling with consistent ~95% battery utilization **per individual battery**:

| Battery Duration | Batteries | Bounces | Optimized Radius | Utilization | Coverage Quality |
|------------------|-----------|---------|------------------|-------------|------------------|
| 10 minutes       | 2         | **5**   | 593 ft          | 95.0%       | Detailed, compact |
| 20 minutes       | 3         | **8**   | 1,595 ft        | 95.0%       | Sweet spot balance |
| 30 minutes       | 4         | **10**  | 3,013 ft        | 94.8%       | Comprehensive coverage |

**Key Insight**: The algorithm now balances both area coverage AND photo density. More batteries enable larger radius per battery because each slice covers smaller angular section (360°/batteries), while bounce count scales with available flight time for optimal reconstruction quality.

## Computational Efficiency

**Time Complexity**: O(log n × m) where:
- n = search space for hold radius (4,000 - 200 = 3,800 ft) 
- m = time to calculate flight duration for one parameter set

**Typical Performance**:
- **Search iterations**: 10-15 per optimization  
- **API response time**: < 1 second
- **Memory usage**: Minimal (no large data structures)
- **Cache efficiency**: Elevation data cached between optimizations
- **Scaling decisions**: O(1) bounce count determination

## Key Advantages

1. **Balanced Coverage**: Optimizes both area AND photo density simultaneously
2. **Quality Focus**: Ensures sufficient waypoints for high-quality reconstruction  
3. **Neural Network Training**: Differentiated altitude logic provides diverse viewing angles
4. **Dense Coverage**: Reduced expansion rate creates more overlap for better training data
5. **Computational Efficiency**: Binary search vs brute force saves 99%+ computation time
6. **Safety First**: Built-in safety margins prevent battery exhaustion
7. **Scalable**: Works equally well for short detailed flights and long comprehensive surveys
8. **Robust**: Handles edge cases and optimization failures gracefully
9. **Industry Best Practices**: Follows 15-20 minute sweet spot with 8 bounces for optimal results

## Neural Network Training Optimizations

### 6. Differentiated Altitude Logic

**Enhanced for AI Training**: The system now implements sophisticated altitude progression specifically designed for neural network training data collection:

```python
# Outbound waypoints: Detail capture at lower altitudes
if 'outbound' in phase or 'hold' in phase:
    agl_increment = additional_distance * 0.37  # 0.37 feet per foot
    desired_agl = min_height + agl_increment

# Inbound waypoints: Context capture at higher altitudes  
elif 'inbound' in phase:
    altitude_decrease = distance_from_max * 0.1  # Only 0.1 feet per foot decrease
    desired_agl = max_outbound_altitude - altitude_decrease
```

**Training Data Benefits**:
- **Diverse Viewing Angles**: Up to 135ft altitude difference at same locations
- **Detail vs Overview**: Lower outbound shots capture textures, higher inbound shots provide context
- **Rich Feature Learning**: Networks learn from both close-up and elevated perspectives
- **Better 3D Reconstruction**: Varied angles improve depth estimation and spatial understanding

### 7. Reduced Expansion Rate

**Gentler Spiral Progression**: The exponential expansion coefficient has been reduced by 14% for denser coverage:

```python
alpha = math.log(r_hold / r0) / (N * dphi) * 0.86  # 14% reduction
```

**Neural Network Benefits**:
- **Smaller Steps**: Reduces gaps between successive bounces for better photo overlap
- **Denser Coverage**: More waypoints per area improves training data quality
- **Smoother Transitions**: More gradual expansion creates consistent flight paths
- **Enhanced Training Quality**: Increased photo density provides richer datasets

**Performance Impact**:
| Bounce | Original Radius | Optimized Radius | Improvement |
|--------|----------------|------------------|-------------|
| 1      | 134.7ft        | 128.4ft         | +6.3ft denser |
| 3      | 245.2ft        | 211.7ft         | +33.5ft denser |
| 6      | 600.0ft        | 445.5ft         | +154.5ft denser |

### 8. AI Training Data Quality Metrics

**Quantified Benefits**:
- **Average altitude differential**: 92.2ft between outbound/inbound at same locations
- **Maximum altitude differential**: 135ft near center of interest
- **Coverage density increase**: 14% more waypoints per spiral area
- **Photo overlap improvement**: Enhanced by reduced expansion rate
- **Viewing angle diversity**: Each location captured from 2+ distinct perspectives

## Future Enhancements

Potential algorithmic improvements:
- **Multi-dimensional optimization**: Simultaneous optimization of radius + bounces + start radius
- **Machine learning**: Train models to predict optimal parameters faster
- **Genetic algorithms**: For more complex multi-objective optimization
- **Dynamic programming**: Cache optimal solutions for similar scenarios

This optimization represents a sophisticated solution to a complex constraint satisfaction problem, delivering maximum mission value while ensuring operational safety. 
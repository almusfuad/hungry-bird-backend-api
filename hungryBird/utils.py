from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile


def validate_image_size(image_file, max_size_kb=200):
    """
    Validates image file size against a maximum size limit (hard limit: 1024KB).
    
    Args:
        image_file: Django UploadedFile object (e.g., request.FILES['image'])
        max_size_kb: Maximum file size in KB (default: 200KB)
    
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'file_size_kb': float (only if valid),
            'max_size_kb': int
        }
    
    Example:
        response = validate_image_size(request.FILES['image'], max_size_kb=500)
        if response['success']:
            # Process image
            pass
        else:
            # Return error to client
            return Response({'error': response['message']}, status=400)
    """
    try:
        max_size_bytes = max_size_kb * 1024
        hard_limit_bytes = 1024 * 1024  # 1024 KB hard limit
        
        # Get file size
        if hasattr(image_file, 'size'):
            file_size = image_file.size
        else:
            # For file-like objects without size attribute
            image_file.seek(0, 2)  # Seek to end
            file_size = image_file.tell()
            image_file.seek(0)  # Reset to beginning
        
        file_size_kb = file_size / 1024
        
        # Check if file exceeds max size or hard limit (1024KB)
        if file_size > max_size_bytes or file_size > hard_limit_bytes:
            return {
                'success': False,
                'message': f'Image size ({file_size_kb:.2f}KB) exceeds maximum allowed size ({max_size_kb}KB)',
                'max_size_kb': max_size_kb
            }
        
        # Validate it's actually an image using Pillow
        try:
            image_file.seek(0)
            img = Image.open(image_file)
            img.verify()  # Verify it's a valid image
            image_file.seek(0)  # Reset file pointer after verification
        except Exception as e:
            return {
                'success': False,
                'message': f'Invalid image file: {str(e)}',
                'max_size_kb': max_size_kb
            }
        
        return {
            'success': True,
            'message': 'Image validation passed',
            'file_size_kb': round(file_size_kb, 2),
            'max_size_kb': max_size_kb
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Error during image validation: {str(e)}',
            'max_size_kb': max_size_kb
        }


def validate_image_dimensions(image_file, min_width=None, min_height=None, max_width=None, max_height=None):
    """
    Validates image dimensions (width and height).
    
    Args:
        image_file: Django UploadedFile object
        min_width: Minimum width in pixels (optional)
        min_height: Minimum height in pixels (optional)
        max_width: Maximum width in pixels (optional)
        max_height: Maximum height in pixels (optional)
    
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'dimensions': (width, height) if valid,
            'constraints': dict
        }
    """
    try:
        image_file.seek(0)
        img = Image.open(image_file)
        width, height = img.size
        image_file.seek(0)
        
        constraints = {
            'min_width': min_width,
            'min_height': min_height,
            'max_width': max_width,
            'max_height': max_height
        }
        
        # Validate constraints
        if min_width and width < min_width:
            return {
                'success': False,
                'message': f'Image width ({width}px) is less than minimum required ({min_width}px)',
                'dimensions': (width, height),
                'constraints': constraints
            }
        
        if min_height and height < min_height:
            return {
                'success': False,
                'message': f'Image height ({height}px) is less than minimum required ({min_height}px)',
                'dimensions': (width, height),
                'constraints': constraints
            }
        
        if max_width and width > max_width:
            return {
                'success': False,
                'message': f'Image width ({width}px) exceeds maximum allowed ({max_width}px)',
                'dimensions': (width, height),
                'constraints': constraints
            }
        
        if max_height and height > max_height:
            return {
                'success': False,
                'message': f'Image height ({height}px) exceeds maximum allowed ({max_height}px)',
                'dimensions': (width, height),
                'constraints': constraints
            }
        
        return {
            'success': True,
            'message': 'Image dimensions validation passed',
            'dimensions': (width, height),
            'constraints': constraints
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Error validating image dimensions: {str(e)}',
            'constraints': {
                'min_width': min_width,
                'min_height': min_height,
                'max_width': max_width,
                'max_height': max_height
            }
        }


def validate_image_format(image_file, allowed_formats=None):
    """
    Validates image file format.
    
    Args:
        image_file: Django UploadedFile object
        allowed_formats: List of allowed formats (e.g., ['JPEG', 'PNG', 'GIF'])
                        Default: ['JPEG', 'PNG']
    
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'format': str (image format if valid),
            'allowed_formats': list
        }
    """
    if allowed_formats is None:
        allowed_formats = ['JPEG', 'JPG', 'PNG']
    
    try:
        image_file.seek(0)
        img = Image.open(image_file)
        image_format = img.format
        image_file.seek(0)
        
        if image_format not in allowed_formats:
            return {
                'success': False,
                'message': f'Image format ({image_format}) is not allowed. Allowed formats: {", ".join(allowed_formats)}',
                'format': image_format,
                'allowed_formats': allowed_formats
            }
        
        return {
            'success': True,
            'message': f'Image format ({image_format}) is valid',
            'format': image_format,
            'allowed_formats': allowed_formats
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Error validating image format: {str(e)}',
            'allowed_formats': allowed_formats
        }


def validate_image_complete(image_file, max_size_kb=200, allowed_formats=None, 
                           min_width=None, min_height=None, max_width=None, max_height=None):
    """
    Complete image validation combining size, format, and dimensions.
    
    Args:
        image_file: Django UploadedFile object
        max_size_kb: Maximum file size in KB (default: 200KB)
        allowed_formats: List of allowed formats (default: ['JPEG', 'PNG'])
        min_width: Minimum width in pixels (optional)
        min_height: Minimum height in pixels (optional)
        max_width: Maximum width in pixels (optional)
        max_height: Maximum height in pixels (optional)
    
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'validations': {
                'size': dict,
                'format': dict,
                'dimensions': dict (if dimension constraints provided)
            }
        }
    """
    validations = {}
    
    # Validate size
    size_validation = validate_image_size(image_file, max_size_kb)
    validations['size'] = size_validation
    
    if not size_validation['success']:
        return {
            'success': False,
            'message': 'Image validation failed',
            'validations': validations
        }
    
    # Validate format
    format_validation = validate_image_format(image_file, allowed_formats)
    validations['format'] = format_validation
    
    if not format_validation['success']:
        return {
            'success': False,
            'message': 'Image validation failed',
            'validations': validations
        }
    
    # Validate dimensions if constraints provided
    if any([min_width, min_height, max_width, max_height]):
        dim_validation = validate_image_dimensions(
            image_file,
            min_width=min_width,
            min_height=min_height,
            max_width=max_width,
            max_height=max_height
        )
        validations['dimensions'] = dim_validation
        
        if not dim_validation['success']:
            return {
                'success': False,
                'message': 'Image validation failed',
                'validations': validations
            }
    
    return {
        'success': True,
        'message': 'All image validations passed',
        'validations': validations
    }


# ============================================================================
# DISTANCE CALCULATION UTILITIES (Haversine Formula)
# ============================================================================

import math

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on Earth using the Haversine formula.
    
    Args:
        lat1 (float): Latitude of first point in decimal degrees
        lon1 (float): Longitude of first point in decimal degrees
        lat2 (float): Latitude of second point in decimal degrees
        lon2 (float): Longitude of second point in decimal degrees
    
    Returns:
        float: Distance in kilometers
    
    Example:
        >>> # Distance from New York to Los Angeles
        >>> distance = calculate_distance(40.7128, -74.0060, 34.0522, -118.2437)
        >>> print(f"{distance:.2f} km")
        3936.31 km
    
    Reference:
        Haversine formula: a = sin²(Δφ/2) + cos φ1 ⋅ cos φ2 ⋅ sin²(Δλ/2)
        c = 2 ⋅ atan2(√a, √(1−a))
        d = R ⋅ c
        where φ is latitude, λ is longitude, R is earth's radius (6371km)
    """
    # Earth's radius in kilometers
    R = 6371.0
    
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Differences in coordinates
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # Distance in kilometers
    distance = R * c
    
    return distance


def filter_drivers_by_radius(drivers_qs, target_lat, target_lon, max_radius_km):
    """
    Filter a queryset of drivers to only include those within a specified radius of a target location.
    
    Args:
        drivers_qs: Django QuerySet of User objects (role=3) with driver_profile
        target_lat (float): Target latitude in decimal degrees
        target_lon (float): Target longitude in decimal degrees
        max_radius_km (float): Maximum radius in kilometers
    
    Returns:
        list: List of tuples (driver_user, distance_km) sorted by distance (nearest first)
    
    Example:
        >>> from django.contrib.auth import get_user_model
        >>> User = get_user_model()
        >>> available_drivers = User.objects.filter(role=3, current_availability__status=1)
        >>> restaurant_lat, restaurant_lon = 40.7128, -74.0060
        >>> nearby = filter_drivers_by_radius(available_drivers, restaurant_lat, restaurant_lon, max_radius_km=10)
        >>> for driver, distance in nearby:
        >>>     print(f"{driver.username}: {distance:.2f} km away")
    
    Note:
        - Assumes drivers have driver_profile with latitude/longitude fields
        - Returns empty list if target coordinates are None/invalid
        - Filters out drivers without valid location data
    """
    if target_lat is None or target_lon is None:
        return []
    
    drivers_with_distance = []
    
    for driver in drivers_qs.select_related('driver_profile'):
        # Skip drivers without profile or location data
        if not hasattr(driver, 'driver_profile'):
            continue
        
        driver_lat = driver.driver_profile.latitude
        driver_lon = driver.driver_profile.longitude
        
        if driver_lat is None or driver_lon is None:
            continue
        
        # Calculate distance
        distance = calculate_distance(target_lat, target_lon, driver_lat, driver_lon)
        
        # Only include if within radius
        if distance <= max_radius_km:
            drivers_with_distance.append((driver, distance))
    
    # Sort by distance (nearest first)
    drivers_with_distance.sort(key=lambda x: x[1])
    
    return drivers_with_distance

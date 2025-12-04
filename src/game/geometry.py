import math

def world_to_screen(view_matrix, pos, width=1920, height=1080):
    """
    Переводит 3D координаты мира в 2D координаты экрана.
    Возвращает (x, y) или None, если враг сзади/за экраном.
    """
    try:
        
        x, y, z = pos
        
        w = view_matrix[12] * x + view_matrix[13] * y + view_matrix[14] * z + view_matrix[15]

        # Если w < 0.01, значит враг позади нас или слишком близко к камере
        if w < 0.01:
            return None

        inv_w = 1.0 / w
        
        screen_x = view_matrix[0] * x + view_matrix[1] * y + view_matrix[2] * z + view_matrix[3]
        screen_y = view_matrix[4] * x + view_matrix[5] * y + view_matrix[6] * z + view_matrix[7]

        # Нормализация координат (-1..1 -> 0..width/height)
        cam_x = width / 2
        cam_y = height / 2

        x_out = cam_x + (cam_x * screen_x * inv_w)
        y_out = cam_y - (cam_y * screen_y * inv_w)

        return int(x_out), int(y_out)

    except Exception:
        return None

def calc_angle(src, dst):
    """Считает углы (pitch, yaw) для аимбота"""
    dx = dst[0] - src[0]
    dy = dst[1] - src[1]
    dz = dst[2] - src[2]
    
    hyp = math.sqrt(dx*dx + dy*dy)
    
    yaw = math.atan2(dy, dx) * 180 / math.pi
    pitch = -math.atan2(dz, hyp) * 180 / math.pi
    
    return pitch, yaw
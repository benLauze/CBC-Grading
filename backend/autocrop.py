"""Automatically detects, straightens, and crops a card from an image."""

import cv2
import numpy as np
from PIL import Image


def auto_crop_card(image: Image.Image, margin=0.02):
    arr = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    edges = cv2.dilate(edges, None, iterations=2)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image

    largest = max(contours, key=cv2.contourArea)

    # Find the smallest rotated rectangle around the card.
    rect = cv2.minAreaRect(largest)
    (cx, cy), (rect_w, rect_h), angle = rect
    if rect_w == 0 or rect_h == 0:
        return image

    img_area = arr.shape[0] * arr.shape[1]
    box_area = rect_w * rect_h

    # Ignore boxes that are too small or cover nearly the entire image.
    if box_area < img_area * 0.15 or box_area > img_area * 0.98:
        return image

    while angle > 45:
        angle -= 90
    while angle <= -45:
        angle += 90

    rot_matrix = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
    h, w = arr.shape[:2]
    straightened = cv2.warpAffine(arr, rot_matrix, (w, h), flags=cv2.INTER_CUBIC,
                                   borderMode=cv2.BORDER_REPLICATE)

    # Apply the same rotation to the rectangle corners.
    box_points = cv2.boxPoints(rect)
    ones = np.ones((4, 1))
    homogeneous = np.hstack([box_points, ones])
    transformed = (rot_matrix @ homogeneous.T).T

    x_coords, y_coords = transformed[:, 0], transformed[:, 1]
    rect_w = x_coords.max() - x_coords.min()
    rect_h = y_coords.max() - y_coords.min()

    # Confirm that the crop has a reasonable card-like aspect ratio.
    long_side = max(rect_w, rect_h)
    short_side = min(rect_w, rect_h)
    if long_side == 0 or not (0.60 <= short_side / long_side <= 0.82):
        return image

    mx = int(rect_w * margin)
    my = int(rect_h * margin)
    x0 = max(0, int(x_coords.min()) - mx)
    y0 = max(0, int(y_coords.min()) - my)
    x1 = min(w, int(x_coords.max()) + mx)
    y1 = min(h, int(y_coords.max()) + my)

    if x1 <= x0 or y1 <= y0:
        return image

    cropped = straightened[y0:y1, x0:x1]
    return Image.fromarray(cropped)

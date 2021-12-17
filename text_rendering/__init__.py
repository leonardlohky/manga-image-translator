
from typing import List
from utils import Quadrilateral
import numpy as np
import cv2
from utils import findNextPowerOf2
from PIL import Image, ImageDraw, ImageFont

from . import text_render

async def dispatch(img_canvas: np.ndarray, text_mag_ratio: np.integer, translated_sentences: List[str], textlines: List[Quadrilateral], text_regions: List[Quadrilateral], force_horizontal: bool) -> np.ndarray :
    """
    Text rendering function for character based texts, e.g. CHS
    """
    for ridx, (trans_text, region) in enumerate(zip(translated_sentences, text_regions)) :
        if not trans_text :
            continue
        if force_horizontal :
            region.majority_dir = 'h'
        print(region.text)
        print(trans_text)
        #print(region.majority_dir, region.pts)
        
        # find font size to fit text inside bounding box
        fg = (region.fg_r, region.fg_g, region.fg_b) # foreground
        bg = (region.bg_r, region.bg_g, region.bg_b) # background
        font_size = 0
        n_lines = len(region.textline_indices)
        for idx in region.textline_indices :
            txtln = textlines[idx]
            #img_bbox = cv2.polylines(img_bbox, [txtln.pts], True, color = fg, thickness=2)
            # [l1a, l1b, l2a, l2b] = txtln.structure
            # cv2.line(img_bbox, l1a, l1b, color = (0, 255, 0), thickness = 2)
            # cv2.line(img_bbox, l2a, l2b, color = (0, 0, 255), thickness = 2)
            #dbox = txtln.aabb
            font_size = max(font_size, txtln.font_size)
            #cv2.rectangle(img_bbox, (dbox.x, dbox.y), (dbox.x + dbox.w, dbox.y + dbox.h), color = (255, 0, 255), thickness = 2)
        font_size = round(font_size)
        #img_bbox = cv2.polylines(img_bbox, [region.pts], True, color=(0, 0, 255), thickness = 2)

        region_aabb = region.aabb
        print(region_aabb.x, region_aabb.y, region_aabb.w, region_aabb.h)

        # round font_size to fixed powers of 2, so later LRU cache can work
        font_size_enlarged = findNextPowerOf2(font_size) * text_mag_ratio
        enlarge_ratio = font_size_enlarged / font_size
        font_size = font_size_enlarged
        while True :
            enlarged_w = round(enlarge_ratio * region_aabb.w)
            enlarged_h = round(enlarge_ratio * region_aabb.h)
            rows = enlarged_h // (font_size * 1.3)
            cols = enlarged_w // (font_size * 1.3)
            if rows * cols < len(trans_text) :
                enlarge_ratio *= 1.1
                continue
            break
        print('font_size:', font_size) # required font size

        # begin placing translated text into respective regions
        tmp_canvas = np.ones((enlarged_h * 2, enlarged_w * 2, 3), dtype = np.uint8) * 127
        tmp_mask = np.zeros((enlarged_h * 2, enlarged_w * 2), dtype = np.uint16)

        if region.majority_dir == 'h' :
            text_render.put_text_horizontal(
                font_size,
                enlarge_ratio * 1.0,
                tmp_canvas,
                tmp_mask,
                trans_text,
                len(region.textline_indices),
                [textlines[idx] for idx in region.textline_indices],
                enlarged_w // 2,
                enlarged_h // 2,
                enlarged_w,
                enlarged_h,
                fg,
                bg
            )
        else :
            text_render.put_text_vertical(
                font_size,
                enlarge_ratio * 1.0,
                tmp_canvas,
                tmp_mask,
                trans_text,
                len(region.textline_indices),
                [textlines[idx] for idx in region.textline_indices],
                enlarged_w // 2,
                enlarged_h // 2,
                enlarged_w,
                enlarged_h,
                fg,
                bg
            )

        tmp_mask = np.clip(tmp_mask, 0, 255).astype(np.uint8)
        x, y, w, h = cv2.boundingRect(tmp_mask)
        r_prime = w / h
        r = region.aspect_ratio
        w_ext = 0
        h_ext = 0
        if r_prime > r :
            h_ext = w / (2 * r) - h / 2
        else :
            w_ext = (h * r - w) / 2
        region_ext = round(min(w, h) * 0.05)
        h_ext += region_ext
        w_ext += region_ext
        src_pts = np.array([[x - w_ext, y - h_ext], [x + w + w_ext, y - h_ext], [x + w + w_ext, y + h + h_ext], [x - w_ext, y + h + h_ext]]).astype(np.float32)
        src_pts[:, 0] = np.clip(np.round(src_pts[:, 0]), 0, enlarged_w * 2)
        src_pts[:, 1] = np.clip(np.round(src_pts[:, 1]), 0, enlarged_h * 2)
        dst_pts = region.pts
        M, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        tmp_rgba = np.concatenate([tmp_canvas, tmp_mask[:, :, None]], axis = -1).astype(np.float32)
        rgba_region = np.clip(cv2.warpPerspective(tmp_rgba, M, (img_canvas.shape[1], img_canvas.shape[0]), flags = cv2.INTER_LINEAR, borderMode = cv2.BORDER_CONSTANT, borderValue = 0), 0, 255)
        canvas_region = rgba_region[:, :, 0: 3]
        mask_region = rgba_region[:, :, 3: 4].astype(np.float32) / 255.0
        img_canvas = np.clip((img_canvas.astype(np.float32) * (1 - mask_region) + canvas_region.astype(np.float32) * mask_region), 0, 255).astype(np.uint8)
    
    return img_canvas

async def dispatch_non_char(image, regions, text, mask, bg_color=255):
    """
    Text rendering function for non-character based texts, e.g. ENG
    """
    # Turn the image into array
    im_array = np.array(image)
    im_array[mask==1] = bg_color
    masked_im = Image.fromarray(im_array)
        
    # Set default font_size to 40
    font_size = 40
    font = ImageFont.truetype("./fonts/mangat.ttf", font_size)
    space = 5
    
    region_list = []
    for region in regions:
        region_aabb = region.aabb
        region_fg = (region.fg_r, region.fg_g, region.fg_b) # foreground
        region_bg = (region.bg_r, region.bg_g, region.bg_b) # background
        region_metadata = ((region_aabb.x, region_aabb.y, region_aabb.w, region_aabb.h), (region_fg, region_bg))
        region_list.append(region_metadata)
        
    for region_data, t in zip(region_list, text):
        # Set default text color to black
        text_color = 0
        # Set default background to white
        bg = 255
        
        # unpack region metadata
        coord = region_data[0]
        color_data = region_data[1]
        
        # Calculate the width and height of text bubbles
        width = coord[2]
        height = coord[3]

        # determine required background and text color
        bg = int((color_data[1][0] + color_data[1][1] + color_data[1][2]) / 3)
        # if im_array[coord[1]:coord[3],coord[0]:coord[2]].mean()<100:
        #     bg = bg_color
        #     text_color = 0
        # Create a new image size equal to the text box

        img = Image.new("1", (width, height), color=bg)
        draw = ImageDraw.Draw(img)
        # Set default coordinates for drawing to 0
        v_coord = 0
        h_coord = 0
        words = t.split()
#         draw.text((v_coord, h_coord), words[0], text_color, font=font)
        if not words:
            words = ['....']
#         print(words)
        lst_word_len, word_height = font.getsize(words[0])
        
        
        for i, word in enumerate(words[1:]):
            font_width, font_height = font.getsize(word)
#             print(width,h_coord,v_coord,font_width,space)
#             print((width-h_coord)<(font_width+space))
            if (width-(h_coord+(lst_word_len + space)))>(font_width+space):
                h_coord += (lst_word_len + space)
                draw.text((h_coord, v_coord), word, text_color, font=font)
                lst_word_len, word_height = font.getsize(word)
            else:
                h_coord = 0
                v_coord += font_size
                draw.text((h_coord, v_coord), word, text_color, font=font)
                lst_word_len,_ = font.getsize(word)
                
        gap = (height - v_coord) / 2 - word_height        
#         img = Image.new("1", (width, height), color=bg)
        draw = ImageDraw.Draw(masked_im)
        # Set default coordinates for drawing to 0
        v_coord = gap
        h_coord = 0
#         print(gap)
        font_size = 40
        
        if gap > 40:
            font_size = 40
        words = t.split()
        if not words:
            words = ['....']
        draw.text((h_coord+coord[0], v_coord+coord[1]), words[0], text_color, font=font)
        lst_word_len,_ = font.getsize(words[0])
        
        for i, word in enumerate(words[1:]):
            font_width, font_height = font.getsize(word)
            if (width-(h_coord+(lst_word_len + space)))>(font_width+space):
                h_coord += (lst_word_len + space)
                draw.text((h_coord+coord[0], v_coord+coord[1]), word, text_color, font=font)
                lst_word_len,_ = font.getsize(word)
            else:
                h_coord = 0
                v_coord += font_size
                draw.text((h_coord + coord[0], v_coord + coord[1]), word, text_color, font=font)
                lst_word_len,_ = font.getsize(word)
    
    masked_im = np.asarray(masked_im)
    return masked_im
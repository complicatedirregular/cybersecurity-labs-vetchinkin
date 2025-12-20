from PIL import Image
import itertools

def str_to_bin(message):
    """Конвертує текст у бінарний рядок."""
    binary = ''.join(format(ord(i), '08b') for i in message)
    return binary

def bin_to_str(binary):
    """Конвертує бінарний рядок у текст."""
    message = ""
    for i in range(0, len(binary), 8):
        byte = binary[i:i+8]
        if len(byte) < 8: break
        message += chr(int(byte, 2))
    return message

def hide_lsb(image_path, output_path, secret_text):
    """Ховає текст у зображення методом LSB."""
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Додаємо маркер кінця повідомлення, щоб знати, де зупинитися
    secret_text += "#####END#####"
    binary_secret = str_to_bin(secret_text)
    data_len = len(binary_secret)
    
    pixels = list(img.getdata())
    new_pixels = []
    
    data_index = 0
    for pixel in pixels:
        if data_index < data_len:
            r, g, b = pixel
            # Змінюємо синій канал (Blue) - він найменш помітний для ока
            # Обнуляємо останній біт і додаємо наш біт
            b = (b & ~1) | int(binary_secret[data_index])
            data_index += 1
            new_pixels.append((r, g, b))
        else:
            new_pixels.append(pixel)
            
    img.putdata(new_pixels)
    img.save(output_path)
    return True

def extract_lsb(image_path):
    """Витягує текст із зображення."""
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')
        
    pixels = list(img.getdata())
    binary_data = ""
    
    for pixel in pixels:
        r, g, b = pixel
        # Читаємо останній біт синього каналу
        binary_data += str(b & 1)

    # Конвертуємо в текст і шукаємо стоп-слово
    full_text = bin_to_str(binary_data)
    stop_marker = "#####END#####"
    
    if stop_marker in full_text:
        return full_text.split(stop_marker)[0]
    else:
        # Якщо маркер не знайдено, повертаємо те, що змогли прочитати (може бути сміття)
        return full_text[:1000]
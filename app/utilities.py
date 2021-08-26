import base64
from io import BytesIO


def img_to_base64_str(img):
    """
    Take in a Pillow image and convert it to a base64 string in PNG format.
    """
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    buffered.seek(0)
    img_byte = buffered.getvalue()
    img_str = "data:image/png;base64," + base64.b64encode(img_byte).decode()
    return img_str


def print_dict(d, indent=''):
    for k in d.keys():
        print(f'{indent}{k}')
        if isinstance(d[k], dict):
            print_dict(d[k], indent + '  ')
        elif isinstance(d[k], list):
            print(f'{indent}[')
            if len(d[k]) and isinstance(d[k][0], dict):
                print_dict(d[k][0], indent + '  ')
            print(f'{indent}]')


def print_hit_structure(hit):
    print('hit:')
    if isinstance(hit, dict):
        print_dict(hit)
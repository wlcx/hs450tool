"""Utility for interacting with the framestore of a Panasonic AV-HS450 vision mixer"""
import socket
import struct
import argparse
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np

PORT = 60010


def get_command(slot):
    assert slot in range(1, 5)
    # The get image command is 0x21 for slot 1, 0x31 for slot 2...
    return bytes([0x11 + (slot * 0x10)])


def put_command(slot):
    # The get image command is 0x24 for slot 1, 0x34 for slot 2...
    assert slot in range(1, 5)
    return bytes([0x14 + (slot * 0x10)])


def buf2image(w, h, buf):
    return Image.frombytes("RGB", (w, h), buf)


def display_pixels(pixel_buffer, width, height):
    root = tk.Tk()
    root.title("Frame")
    canvas = tk.Canvas(root, width=width, height=height)
    canvas.pack()
    image = buf2image(width, height, pixel_buffer)
    photo = ImageTk.PhotoImage(image)
    canvas.create_image(0, 0, anchor=tk.NW, image=photo)
    root.mainloop()


def get_frame(sock, slot):
    """Get a frame from a slot on the HS450.

    Returns a tuple: width, height, image data bytearray
    """
    sock.send(get_command(slot))
    b = sock.recv(1)
    assert b[0] == 0x10
    w, h = struct.unpack(">HH", sock.recv(4))
    imgbuffer = bytearray()
    while True:
        data = sock.recv(1024)
        if not data:
            break
        imgbuffer += data
    assert w * h * 2 == len(
        imgbuffer
    ), f"Unexpected img data len: expected {w*h*2} got {len(imgbuffer)}"
    return w, h, imgbuffer


def put_frame(sock, slot, w, h, data):
    """Put a frame into a slot on the HS450."""
    sock.settimeout(10)
    assert w * h * 2 == len(
        data
    ), f"Unexpected img data len: expected {w*h*2} got {len(data)}"
    print("Sending...")
    sock.send(put_command(slot))
    assert sock.recv(1)[0] == 0xAC
    sock.send(struct.pack(">HH", w, h))
    sock.sendall(data)
    print("Waiting for HS450 to finish storing...")
    assert sock.recv(1)[0] == 0xAC


# Transform from https://web.archive.org/web/20180421030430/http://www.equasys.de/colorconversion.html
ycbcr_to_rgb = np.matrix(
    [[1.164, 0, 1.793], [1.164, -0.213, -0.533], [1.164, 2.112, 0]]
)  # limited range
rgb_to_ycbcr = np.matrix(
    [[0.183, 0.614, 0.062], [-0.101, -0.339, 0.439], [0.439, -0.399, -0.040]]
)  # limited range


def hdtv_ycbcr2rgb(y, cb, cr):
    return (
        np.clip(
            np.matmul(ycbcr_to_rgb, np.matrix([[y - 16], [cb - 128], [cr - 128]])),
            0,
            255,
        )
        .astype(np.uint8)
        .tobytes()
    )


def ycbycr2rgb(buf):
    rgb = bytearray()
    count = 0
    while count < len(buf):
        y1, cb, y2, cr = buf[count], buf[count + 1], buf[count + 2], buf[count + 3]
        rgb += hdtv_ycbcr2rgb(y1, cb, cr)
        rgb += hdtv_ycbcr2rgb(y2, cb, cr)
        count += 4
        if (count / 4) % 10000 == 0:
            print(".", end="", flush=True)
    return rgb


def hdtv_rgb2ycrcb(r, g, b):
    return (
        np.clip(
            np.array([[16], [128], [128]])
            + np.matmul(rgb_to_ycbcr, np.array([[r], [g], [b]])),
            0,
            255,
        )
        .astype(np.uint8)
        .tobytes()
    )


def rgb_to_ycbcr422(raw):
    assert len(raw) % 3 == 0
    out = bytearray()
    i = 0
    while i < len(raw):
        # Consider 2 pixels at a time
        y1, cb1, cr1 = hdtv_rgb2ycrcb(*raw[i : i + 3])
        y2, cb2, cr2 = hdtv_rgb2ycrcb(*raw[i + 3 : i + 6])
        # Subsample the chromas
        out.extend(bytes([y1, int((cb1 + cb2) / 2), y2, int((cr1 + cr2) / 2)]))
        i += 6
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ip_address", help="IP address of device")
    parser.add_argument("operation", choices=("get", "put"))
    parser.add_argument(
        "slot", type=int, choices=range(1, 5), help="Slot value (integer in range 1-4)"
    )
    parser.add_argument("file", type=str, help="Image file to send or receive")
    parser.add_argument("--display", action="store_true", help="Show the frame")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        if args.operation == "get":
            sock.connect((args.ip_address, PORT))
            w, h, imgdata = get_frame(sock, args.slot)
            print(f"Got {w}x{h} frame")
            with open(args.file, "wb") as f:
                buf2image(w, h, ycbycr2rgb(imgdata)).save(f)
        elif args.operation == "put":
            im = Image.open(args.file)
            buf = rgb_to_ycbcr422(im.tobytes())
            sock.connect((args.ip_address, PORT))
            put_frame(sock, args.slot, im.width, im.height, buf)
        else:
            raise NotImplementedError()
    except socket.timeout:
        print("Connection timed out.")
    finally:
        sock.close()

    if args.display:
        display_pixels(ycbycr2rgb(imgdata), w, h)


if __name__ == "__main__":
    main()

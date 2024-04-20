# Panasonic AV-HS450 Image Transmission Tool (open source edition)

This is a command line tool for sending/receiving images to/from the Panasonic AV-HS450
vision mixer's frame store, and a simpler open source replacement for Panasonic's own
tool which is windows-only and tricky to find.

The mixer has 4 frame store slots. Each can hold a still image.

## ⚠️ Warning
I have tested this on my own hardware and it didn't screw anything up, but your milage
may vary - use at your own risk!

## Usage
`hs450tool.py <ip of mixer> <get|put> <slot number> filepath`
 When getting, the received image is saved to `filepath`. When putting, the image at
 `filepath` is sent.


## The protocol
It's a binary, on TCP port `60010`.

### Getting images from the frame store
- Open the connection
- We send the one byte fetch command. The first nibble is `slot number + 1`, the second
  nibble is `1`. So `0x21` for slot 1, `0x31` for slot 2, etc.
- Mixer sends back `0x10` (presumably some kind of acknowledgement)
- Mixer sends 4 bytes describing the dimensions of the image: 2 bytes for width, 2 for
  height. These are big-endian, so `0x07 0x80 0x04 0x38` is a width of `1920` and
  height of `1080`.
- Mixer sends the image data. See [image format](#image-format).

### Putting images in the frame store
- Open connection
- We send the one byte fetch command. The first nibble is `slot number + 1`, the second
  nibble is `4`. So `0x24` for slot 1, `0x34` for slot 2, etc.
- Mixer sends `0xAC` (presumably to acknowledge)
- We send 4 bytes describing the image dimensions - this is in the same format as above.
- We send the image data
- The mixer sends `0xAC` when it's done storing the frame. This can be several seconds
  after we send the last image data - so make sure your socket doesn't timeout!

## Image format
The mixer sends and receives image data encoded as YCbCr 4:2:2, also sometimes known as
"YUY2". This means that a pair of sequential pixels is encoded as 4 bytes, $Y_1$ $C_B$
$Y_2$ $C_R$, where:
- $Y_1$ and $Y_2$ are the luma components of the first and second pixels in the pair,
  respectively
- $C_B$ and $C_R$ are the blue-difference and red-difference chroma components of *both
  pixels*.
This is the same image format as HD-SDI, but 8 bit rather than 10 bit.



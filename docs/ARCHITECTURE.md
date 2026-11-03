# Architecture

The ATmega32U4 performs two USB roles at once:

1. The MAX3421E on the USB Host Shield hosts the wired Xbox Series X controller over SPI.
2. The Leonardo native USB peripheral exposes the PS4-style device interface.

`XboxInput.cpp` maps Xbox buttons, sticks, triggers, and Share to PS4 reports. Share is exposed as a touchpad click; neutral touch coordinates keep the PS4 keyboard in directional-input mode.

`Ps4Auth.cpp` collects five F0 pages into the 256-byte challenge, reports F2 busy while signing, constructs the 1,064-byte response, and serves it as nineteen F1 pages. Repeated and interrupted exchanges are traced without logging challenge or credential bytes.

`Signer.cpp` performs SHA-256, MGF1, PSS encoding with a 32-byte salt, two 1,024-bit CRT exponentiations, and Garner recombination. The current arithmetic separates reverse-product-scanning multiplication/squaring from hybrid-scanning Montgomery reduction. Credential-dependent constants remain in ignored local headers.

USB interrupts remain enabled during signing. The signer services the host/controller path cooperatively between complete modular operations.


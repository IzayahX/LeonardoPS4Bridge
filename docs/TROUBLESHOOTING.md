# Troubleshooting

## The firmware does not compile

Confirm that the selected board is `experimental:ps4avr:leonardo`, not stock `arduino:avr:leonardo`. The custom core contains the endpoint-zero authentication callbacks and descriptor changes.

Confirm that all four core patches were applied in order and `touchpad-neutral.patch` was applied to the pinned PS4Arduino commit. Patch failures usually mean the wrong commit or an already modified checkout.

`private_crt.h` and `public_identity.h` must exist beside the sketch. Generate them locally; never copy them into an issue.

## Flash overflow

The reference build has only 210 bytes free. Confirm link-time optimization is active, use the pinned versions, and avoid debug strings or Serial. A different library version can pull additional code into the image.

## Xbox controller is not detected

- Verify the Host Shield is connected through the Leonardo ICSP/SPI pins.
- Use a data-capable Xbox USB-C cable.
- Confirm the shield's power arrangement is appropriate for the controller.
- Test the upstream `XBOXONE` example before debugging PS4 behavior.
- Reconnect only the Xbox cable after the Leonardo firmware is already running.

## PS4 sees the controller but no buttons work

First separate enumeration from Xbox input. If the PS4 sees the device but the Host Shield flags show disconnected, debug the host side. If both host and Xbox flags are set, inspect report mapping and the PS4 input endpoint.

## Keyboard shows a floating touch circle

Use the pinned `no-pointer-capabilities.patch` and `touchpad-neutral.patch`. The bridge retains the touchpad button while advertising/holding neutral pointer data so D-pad keyboard navigation remains available.

## F2 remains busy forever

Read F4 diagnostics. Check `signer_starts`, `signatures_ready`, `signatures_aborted`, cancellation reason, F3/USB resets and maximum busy age. A signature can be locally correct yet discarded when the authentication epoch changes.

## F2 is ready but no F1 pages are committed

This occurred when an older local USB core was selected. Confirm the pinned core includes `ps4AuthCommit()` and that the core advances the page only after the complete control response is queued.

## F1 repeats page zero

The wrong or partially patched core is the leading cause. Rebuild from the pinned PS4Arduino-AVR commit and reapply patches in order.

## Signatures verify, all F1 pages are sent, but input stops at eight minutes

That is the current tested outcome. Verify the trace first: groups of nineteen F1 pages, page 18 last, F2 ready and zero malformed reports rule out common transport errors. If those pass, the remaining issue is console acceptance of the credential identity or an as-yet-unidentified identity-specific requirement. Local cryptographic validity is necessary but not sufficient.

Do not try to solve this by spoofing only VID/PID/descriptors or reconnecting every eight minutes.

## Diagnostics disappear after moving back to Windows

The EEPROM snapshot begins after 150 seconds and refreshes every 60 seconds. Leave the Leonardo connected for at least one minute after the event of interest and a few extra seconds before moving the cable. Do not flash before reading F4.


# Slack app icon

`acme-bank-slack-icon.png` is the 2000 x 2000 icon for the Acme Bank Slack apps (`config/slack/`). It is the Borrower Portal brand mark from `los-salesforce-project/.../losreactapp/src/styles.css`, scaled up: an amber ring and serif `AB` monogram on the primary evergreen, over the rail's deep evergreen ground.

Colours are the portal tokens only: `#0A332E` (ground), `#0F4C45` (mark), `#C9871A` (amber). The ground fades to a flat `#0A332E` at the edges, the same value as the manifest `background_color`, so the icon and the Slack app tile read as one surface. The artwork is full bleed with square corners and no shadow of its own: Slack rounds the corners itself and paints a gradient banner over the background colour, so any inset margin or transparent edge shows as a square or a white frame in the app preview. The mark clears Slack's corner rounding with room to spare.

`acme-bank-slack-icon.svg` is the editable source. The PNG was rendered from it in headless Chromium with the Gelasio Medium webfont (a Georgia-compatible serif, SIL OFL) for the monogram:

```sh
chrome --headless=new --hide-scrollbars --force-device-scale-factor=1 --window-size=2000,2200 \
  --virtual-time-budget=4000 --screenshot=icon.png acme-bank-slack-icon.svg   # then crop to 2000x2000
```

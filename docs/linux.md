# Emkay on Linux and the Raspberry Pi

An old laptop, a mini PC or a Raspberry Pi with a small screen: on Linux, Emkay runs in Chromium in
kiosk mode. The helper script [`emkay-kiosk.sh`](../scripts/linux/emkay-kiosk.sh) sets it up on the
common distributions.

## Two ways

| | **Desktop** (default) | **Dedicated** |
|---|---|---|
| What | Emkay starts full screen when you log in to your normal desktop | The machine boots straight into Emkay, nothing else |
| For | A PC or laptop you also use for other things | A machine that *is* an Emkay: a Pi with a screen, a mini PC on the wall |
| How | An autostart entry for your user | Its own `emkay` user, [cage](https://github.com/cage-kiosk/cage) (a kiosk shell that shows one app full screen) and [greetd](https://sr.ht/~kennylevinsen/greetd/) (logs it in at boot) |
| Undo | `--uninstall` | `--uninstall`, which brings the old login screen back |

Both ways also:

- let Emkay's address use the **microphone** and **play sound** without asking (Chromium policies
  `AudioCaptureAllowedUrls` and `AutoplayAllowlist` in `/etc/chromium/policies/managed/emkay.json`);
- install **PipeWire** if the machine has no sound server yet;
- make **USB microphones and speakers win** over HDMI and the jack, with a small WirePlumber rule.
  The script writes it in the right format for WirePlumber 0.4 (Debian 12) and 0.5 (most others).

Chromium keeps its profile, so Emkay's settings, skills and speech models survive a restart.

## Supported distributions

| Distribution | Status |
|---|---|
| Debian 12 and newer | ✓ |
| Raspberry Pi OS (Bookworm and newer), Lite and Desktop | ✓ |
| Fedora | ✓ |
| Arch Linux and its relatives | ✓ |
| openSUSE | ✓ |
| Ubuntu | Not yet. Ubuntu only has Chromium as a snap, which ignores the system's Chromium policies. You can still open <https://app.emkay.ai> in any browser, allow the microphone once, and add it to your startup apps by hand. |

This is early alpha. The script has been checked with shellcheck and its dry run, not yet on every
distribution, so please try `--dry-run` first. Reports are welcome in
[Emkay's Discussions](https://github.com/emkay-voice/emkay/discussions).

## Using the script

```bash
curl -fsSLO https://raw.githubusercontent.com/emkay-voice/emkay-kiosk/main/scripts/linux/emkay-kiosk.sh
chmod +x emkay-kiosk.sh

./emkay-kiosk.sh --dry-run               # see what it would do, changes nothing
sudo ./emkay-kiosk.sh                    # desktop way, for the user running sudo
sudo ./emkay-kiosk.sh --dedicated        # dedicated way (asks before replacing the login screen)
sudo ./emkay-kiosk.sh --url https://my-emkay-home.local   # your own Emkay Home
sudo ./emkay-kiosk.sh --uninstall        # undo
```

| Option | Meaning |
|---|---|
| `--url URL` | Emkay's address. Default `https://app.emkay.ai` |
| `--desktop` / `--dedicated` | Which way (default: desktop) |
| `--user NAME` | Desktop: whose desktop. Dedicated: the kiosk user's name (default `emkay`) |
| `--yes` | Don't ask before replacing the login screen |
| `--dry-run` | Only show what would happen |
| `--uninstall` | Remove everything the script added. The `emkay` user and its data are kept |

It prints one line per step and writes the details to `/var/log/emkay-kiosk.log`.

## Raspberry Pi

**Which Pi?** Emkay does speech recognition and speech on the device, and that is heavy work for
a browser.

- **Raspberry Pi 5 (8 GB)** is the one to choose for Emkay on its own.
- **Raspberry Pi 4** will probably need help with the speech: an [Emkay Home](https://github.com/emkay-voice/emkay-home)
  on a stronger machine, or OpenVoiceOS' servers. Reports of how it does are very welcome.
- Older Pis are too slow for Emkay in a browser.

**Setting up a dedicated Pi:**

1. Flash **Raspberry Pi OS Lite (64-bit)** with Raspberry Pi Imager. Set user, Wi-Fi and SSH in
   Imager's settings.
2. Connect a screen. The official Raspberry Pi Touch Display and most HDMI screens work as they are.
3. Plug in a **USB microphone** (or a USB conference speaker) and a speaker. Use USB or HDMI sound,
   because the Pi 4's jack is noisy and the Pi 5 has none.
4. Log in (or SSH in) and run:

   ```bash
   curl -fsSLO https://raw.githubusercontent.com/emkay-voice/emkay-kiosk/main/scripts/linux/emkay-kiosk.sh
   chmod +x emkay-kiosk.sh
   sudo ./emkay-kiosk.sh --dedicated
   sudo reboot
   ```

On **Raspberry Pi OS with Desktop**, the normal desktop way works too: `sudo ./emkay-kiosk.sh`.

**Microphone boards (HATs)** on the Pi's pins, like ReSpeaker or the Mark II's SJ201, need their own
drivers and overlays. They are not covered here. A USB microphone just works.

## Good to know

- **Screen sleep:** cage never blanks the screen. On a desktop, say *"Hey Emkay, keep the screen on"*
  or turn screen blanking off in the desktop's settings.
- **Leaving Emkay:** in desktop mode, Alt+F4 closes it. In dedicated mode, switch to a text console
  with Ctrl+Alt+F2 (or log in over SSH).
- **Wrong microphone?** Emkay uses the system's default microphone. Pick it in the desktop's sound
  settings, or with `wpctl status` and `wpctl set-default <id>` on a machine without a desktop.
- **Your own Emkay Home** has its own certificate. Install it first, as described in
  [Emkay Home's README](https://github.com/emkay-voice/emkay-home).

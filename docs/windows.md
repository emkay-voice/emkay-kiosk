# Emkay on a Windows PC or laptop

An old laptop in the kitchen or a small PC behind a screen on the wall: Windows can start Emkay full
screen by itself, ready to listen. One small helper script does the parts that would otherwise mean
digging through the registry.

## Why not Windows' own kiosk?

Windows has a built-in kiosk (*Settings → Accounts → Other users → Set up a kiosk*). It locks the
PC to Microsoft Edge nicely, but Edge's kiosk mode always runs **InPrivate**. Then Emkay forgets
everything at each restart: its settings, your skills and the speech models it downloaded, which
take a while to fetch. So this guide uses an ordinary user account that signs in by itself and
starts Emkay full screen. This keeps Emkay's data, but it is not locked down. Someone at the
keyboard can still press Alt+Tab. For a PC at home that is usually just right.

## 1. A user for Emkay

Ideally the PC is only used for Emkay. If not, make a separate local account for it: **Settings →
Accounts → Other users → Add account → I don't have this person's sign-in information → Add a user
without a Microsoft account**. Then sign in to that account once.

## 2. Let Windows sign in by itself

Pick one of these:

- **Sysinternals Autologon** (Microsoft's own small tool, <https://learn.microsoft.com/sysinternals/downloads/autologon>):
  run it, enter the account and password, and click **Enable**. The password is stored encrypted.
- **netplwiz**: press Win+R, type `netplwiz`, select the account, untick *Users must enter a user
  name and password*, and enter the password. On Windows 11, the tick box only shows after you turn
  off **Settings → Accounts → Sign-in options → For improved security, only allow Windows Hello
  sign-in**.

## 3. Run the helper script

1. Download [`emkay-kiosk.ps1`](../scripts/windows/emkay-kiosk.ps1).
2. Open **PowerShell as administrator** (right-click Start → *Terminal (Admin)*).
3. Allow the script for this one window and see what it would do:

   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\emkay-kiosk.ps1 -WhatIf
   ```

4. Run it for real. Add `-Url` with your Emkay Home's address if you have one:

   ```powershell
   .\emkay-kiosk.ps1
   .\emkay-kiosk.ps1 -Url https://my-emkay-home.local
   ```

The script:

| What | How |
|---|---|
| Microphone and sound without asking | Edge policies `AudioCaptureAllowedUrls` and `AutoplayAllowlist` for Emkay's address |
| Emkay starts at sign-in | A shortcut in the all-users Startup folder: `msedge --app=<url> --start-fullscreen` |
| Screen stays on | Power plan: never turn off the screen or sleep while plugged in |

`.\emkay-kiosk.ps1 -Remove` takes the policies and the shortcut away again.

## 4. Restart

Windows signs in, and Emkay opens full screen. The first start downloads Emkay's speech models,
so give it a few minutes. After that it starts much faster.

## Microphone

Laptops have a microphone built in. For a desktop PC, any **USB microphone** or USB conference
speaker works without drivers. Emkay uses Windows' default microphone, so if
Windows picks the wrong one, set it under **Settings → System → Sound → Input**.

## Good to know

- **F11** leaves full screen, and **Alt+F4** closes Emkay. It comes back at the next sign-in.
- Turn on **Do Not Disturb** (*Settings → System → Notifications*), so pop-ups don't cover Emkay's face.
- Windows Update can restart the PC at night. Set **active hours** under *Settings → Windows Update
  → Advanced options*. Emkay starts again by itself after a restart anyway.
- A laptop that is always plugged in: many makers offer a charging limit in their own app (Lenovo
  Vantage, Dell Power Manager, MyASUS, …), and it is worth turning on.

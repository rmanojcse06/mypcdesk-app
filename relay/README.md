# WhatsApp remote for MyDesk

Message your PC on WhatsApp: `status`, `awake 2h`, `clip <link>`, `events`, `say …`.

```
WhatsApp ──webhook──▶ your relay (Cloudflare Worker, free) ◀──outgoing poll every 5 s── MyDesk on your PC
MyDesk ──reply──▶ WhatsApp Cloud API (official)
```

Your PC never accepts connections from the internet. The relay stores only messages from numbers you allow, and MyDesk only runs the fixed commands below — never shell commands.

**Cost:** WhatsApp charges per message, but free-form replies inside the 24-hour window after *you* message are free ([Meta pricing](https://developers.facebook.com/docs/whatsapp/pricing)). Cloudflare Workers and D1 free plans cover this easily. MyDesk never messages you first, so normal use costs nothing.

## Commands

| Send | MyDesk does |
| --- | --- |
| `status` | Replies if the PC is on, uptime, CPU, battery, stay-awake state, upcoming events |
| `awake 2h` / `awake 90m` | Doesn't sleep for that long (only while on the charger) |
| `awake until python` | Doesn't sleep until that program finishes |
| `sleep ok` | Normal sleep again |
| `clip <link>` | Saves the reel/video with Clip Maker, messages you when done |
| `events` | Next 15 days from your calendar |
| `ports` | Listening ports, highlighting ones reachable from your network |
| `say <text>` | Pops the text up on your screen |
| `show` | Brings MyDesk to the front |
| `help` | This list |

A message can't switch on a PC that is asleep or off. That needs Wake-on-LAN from another device on your home network; `awake` is what stops it falling asleep in the first place.

## Setup (about 30 minutes, once)

### 1. Meta (WhatsApp Cloud API)

1. Go to [developers.facebook.com](https://developers.facebook.com/), **Create app**, choose the **Business** type, and add the **WhatsApp** product.
2. In **WhatsApp → API Setup** Meta gives you a free **test phone number**. Note its **Phone number ID**.
3. Under **To**, add **your own WhatsApp number** and confirm it with the code Meta sends.
4. **App settings → Basic**: copy the **App secret**.
5. Make a long-lived token: **Business settings → Users → System users → Add**, then **Generate token** for your app with the `whatsapp_business_messaging` permission. (The token on the API Setup page expires after a day.)

### 2. Cloudflare relay

Needs Node.js. In this `relay` folder:

```bash
npx wrangler login
npx wrangler d1 create mydesk-relay          # paste the printed database_id into wrangler.toml
npx wrangler d1 execute mydesk-relay --remote --file schema.sql
npx wrangler secret put VERIFY_TOKEN         # any random text, e.g. from a password generator
npx wrangler secret put APP_SECRET           # from step 1.4
npx wrangler secret put RELAY_KEY            # another long random text
npx wrangler secret put ALLOWED_NUMBERS      # your number, digits only with country code: 9198xxxxxxxx
npx wrangler deploy                          # prints https://mydesk-relay.<you>.workers.dev
```

### 3. Connect Meta to the relay

**WhatsApp → Configuration → Webhook → Edit**: callback URL `https://mydesk-relay.<you>.workers.dev/webhook`, verify token = your `VERIFY_TOKEN`. Then **Manage** webhook fields and subscribe to **messages**.

### 4. Turn it on in MyDesk

In `config.json` on your PC:

```json
"whatsapp": {
  "enabled": true,
  "relay_url": "https://mydesk-relay.<you>.workers.dev",
  "relay_key": "<your RELAY_KEY>",
  "phone_number_id": "<from step 1.2>",
  "access_token": "<system-user token from step 1.5>",
  "graph_version": "v23.0",
  "poll_seconds": 5
}
```

Restart MyDesk, then WhatsApp the test number: `status`.

## Keeping it safe

- `config.json` holds your token and stays on your PC (it's git-ignored). Treat it like a password.
- Only numbers in `ALLOWED_NUMBERS` reach MyDesk; everything else is dropped by the relay.
- Every webhook is checked against your App secret, so nobody can fake messages to the relay.
- Every remote command also pops up on your screen.
- To switch it off, set `"enabled": false` or delete the worker with `npx wrangler delete`.

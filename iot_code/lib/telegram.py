import requests


def tg_send_message(token, chat_id, text, parse_mode=None, disable_notification=False, ujson=None):
    url = "https://api.telegram.org/bot{}/sendMessage".format(token)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_notification": disable_notification
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode  # "MarkdownV2" or "HTML"
    # Telegram accepts JSON body
    headers = {"Content-Type": "application/json"}
    r = None
    try:
        r = requests.post(url, data=ujson.dumps(payload), headers=headers)
        if r.status_code != 200:
            raise RuntimeError("Telegram error {}: {}".format(r.status_code, r.text))
        res = r.json()
        if not res.get("ok"):
            raise RuntimeError("Telegram API returned ok=false: {}".format(res))
        return res["result"]
    finally:
        if r is not None:
            r.close()

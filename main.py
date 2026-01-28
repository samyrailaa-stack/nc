\from flask import Flask, render_template, request, jsonify
import threading
import time
import random
import os
import gc
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

app = Flask(__name__)
app.secret_key = "sujal_hawk_nc_2026"

state = {"running": False, "changed": 0, "logs": [], "start_time": None}
cfg = {
    "sessionid": "",
    "thread_ids": [],  # list of thread_ids
    "names": [],       # list of name change texts
    "nc_delay": 60,    # seconds between NC cycles
}

# Device rotation list (2025-2026 realistic devices)
DEVICES = [
    {
        "deviceName": "Pixel 9 Pro",
        "width": 1080,
        "height": 2400,
        "pixelRatio": 3.0,
        "mobile": True,
        "userAgent": "Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro Build/AP3A.250105.001) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.58 Mobile Safari/537.36 Instagram 330.0.0.45.112 Android (35/15; 480dpi; 1080x2400; Google; Pixel 9 Pro; raven; raven; en_US)"
    },
    {
        "deviceName": "Galaxy S24 Ultra",
        "width": 1080,
        "height": 2340,
        "pixelRatio": 3.0,
        "mobile": True,
        "userAgent": "Mozilla/5.0 (Linux; Android 15; SM-S928B Build/AP3A.250105.001) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.58 Mobile Safari/537.36 Instagram 331.0.0.38.120 Android (35/15; 480dpi; 1080x2340; samsung; SM-S928B; dm3q; dm3q; en_US)"
    },
    {
        "deviceName": "OnePlus 12",
        "width": 1080,
        "height": 2400,
        "pixelRatio": 3.0,
        "mobile": True,
        "userAgent": "Mozilla/5.0 (Linux; Android 15; CPH2653 Build/AP3A.250105.001) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.58 Mobile Safari/537.36 Instagram 329.0.0.55.99 Android (35/15; 480dpi; 1080x2400; OnePlus; CPH2653; OnePlus12; OnePlus12; en_US)"
    },
    {
        "deviceName": "Xiaomi 14 Pro",
        "width": 1080,
        "height": 2400,
        "pixelRatio": 3.0,
        "mobile": True,
        "userAgent": "Mozilla/5.0 (Linux; Android 15; 24053PY3BC Build/AP3A.250105.001) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.58 Mobile Safari/537.36 Instagram 332.0.0.29.110 Android (35/15; 480dpi; 1080x2400; Xiaomi; 24053PY3BC; shennong; shennong; en_US)"
    }
]

def log(msg):
    entry = f"[{time.strftime('%H:%M:%S')}] {msg}"
    state["logs"].append(entry)
    if len(state["logs"]) > 500:
        state["logs"] = state["logs"][-500:]
    print(entry)
    gc.collect()
    log_memory()

def log_memory():
    memory_usage = gc.get_count()
    entry = f"[MEMORY] Garbage collected. Current count: {memory_usage}"
    state["logs"].append(entry)
    print(entry)

def change_group_name(driver, thread_id, new_name):
    try:
        url = f"https://www.instagram.com/direct/t/{thread_id}/"
        driver.get(url)
        time.sleep(random.uniform(3, 5))

        # Open info (pr.py selector)
        info_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "svg[aria-label='Conversation information']"))
        )
        info_button.click()
        time.sleep(2)

        # Click change
        change_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[text()='Change']"))
        )
        change_button.click()
        time.sleep(2)

        # Enter new name
        input_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@aria-label='Group name']"))
        )
        input_field.send_keys(Keys.CONTROL + "a")
        input_field.send_keys(Keys.DELETE)
        input_field.send_keys(new_name)

        # Save
        save_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[text()='Save']"))
        )
        save_button.click()
        time.sleep(2)

        log(f"NC SUCCESS → {new_name} for thread {thread_id}")
        state["changed"] += 1
        return True

    except Exception as e:
        log(f"NC FAILED for thread {thread_id}: {str(e)[:80]}")
        return False

def nc_loop():
    cycle = 0
    while state["running"]:
        log(f"NC CYCLE {cycle + 1} started")

        # New device rotation har cycle pe
        device = random.choice(DEVICES)
        log(f"Using device: {device['deviceName']} for this cycle")

        options = uc.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-notifications")

        # Apply device emulation
        options.add_experimental_option("mobileEmulation", device)

        driver = uc.Chrome(options=options)

        # Fast login with sessionid
        driver.get("https://www.instagram.com")
        driver.add_cookie({"name": "sessionid", "value": cfg["sessionid"], "domain": ".instagram.com"})
        driver.refresh()
        time.sleep(3)  # Fast wait
        log("Logged in with sessionid (device rotated)")

        # Rotate name
        name_index = cycle % len(cfg["names"])
        new_name = cfg["names"][name_index]

        for thread_id in cfg["thread_ids"]:
            change_group_name(driver, thread_id, new_name)
            time.sleep(4)  # Small wait between threads

        cycle += 1
        log(f"Cycle completed. Waiting {cfg['nc_delay']} sec for next")

        # Restart driver for memory clean + new device next cycle
        driver.quit()
        gc.collect()
        gc.collect()  # Double collect for safety
        log_memory()
        time.sleep(cfg["nc_delay"])

    log("NC LOOP STOPPED")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    global state, cfg
    state["running"] = False
    time.sleep(1)

    state = {"running": True, "changed": 0, "logs": ["STARTED"], "start_time": time.time()}

    accounts_raw = request.form["accounts"].strip().split("\n")
    cfg["sessionid"] = accounts_raw[0].split(":")[0].strip()  # Single sessionid
    cfg["thread_ids"] = [line.split(":")[1].strip() for line in accounts_raw if line.strip()]

    cfg["names"] = [n.strip() for n in request.form["names"].split("\n") if n.strip()]
    cfg["nc_delay"] = float(request.form.get("nc_delay", "60"))

    threading.Thread(target=nc_loop, daemon=True).start()
    log(f"STARTED NC LOOP WITH {len(cfg['thread_ids'])} GROUPS | Device rotation enabled")

    return jsonify({"ok": True})

@app.route("/stop")
def stop():
    state["running"] = False
    log("STOPPED BY USER")
    return jsonify({"ok": True})

@app.route("/status")
def status():
    uptime = "00:00:00"
    if state.get("start_time"):
        t = int(time.time() - state["start_time"])
        h, r = divmod(t, 3600)
        m, s = divmod(r, 60)
        uptime = f"{h:02d}:{m:02d}:{s:02d}"
    return jsonify({
        "running": state["running"],
        "changed": state["changed"],
        "uptime": uptime,
        "logs": state["logs"][-100:]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

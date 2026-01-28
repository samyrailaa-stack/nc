from flask import Flask, render_template, request, jsonify
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
app.secret_key = "sujal_hawk_nc_fix_2026"

state = {"running": False, "changed": 0, "logs": [], "start_time": None}
cfg = {
    "sessionid": "",
    "thread_ids": [],
    "names": [],
    "nc_delay": 60,
}

DEVICES = [
    {"deviceName": "Pixel 9 Pro", "width": 1080, "height": 2400, "pixelRatio": 3.0, "mobile": True,
     "userAgent": "Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro Build/AP3A.250105.001) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.58 Mobile Safari/537.36 Instagram 330.0.0.45.112 Android (35/15; 480dpi; 1080x2400; Google; Pixel 9 Pro; raven; raven; en_US)"},
    {"deviceName": "Galaxy S24 Ultra", "width": 1080, "height": 2340, "pixelRatio": 3.0, "mobile": True,
     "userAgent": "Mozilla/5.0 (Linux; Android 15; SM-S928B Build/AP3A.250105.001) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.58 Mobile Safari/537.36 Instagram 331.0.0.38.120 Android (35/15; 480dpi; 1080x2340; samsung; SM-S928B; dm3q; dm3q; en_US)"},
]

def log(msg, important=False):
    entry = f"[{time.strftime('%H:%M:%S')}] {msg}"
    if important:
        entry = f"★★★ {entry} ★★★"
    state["logs"].append(entry)
    print(entry)
    gc.collect()

def change_group_name(driver, thread_id, new_name):
    try:
        url = f"https://www.instagram.com/direct/t/{thread_id}/"
        driver.get(url)
        time.sleep(random.uniform(4, 7))

        info_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "svg[aria-label='Conversation information']"))
        )
        info_button.click()
        time.sleep(3)

        change_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Change')]"))
        )
        change_button.click()
        time.sleep(3)

        input_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@aria-label='Group name' or contains(@placeholder, 'name')]"))
        )
        input_field.send_keys(Keys.CONTROL + "a")
        input_field.send_keys(Keys.DELETE)
        input_field.send_keys(new_name)

        save_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(),'Save') or @role='button' and contains(text(),'Save')]"))
        )
        save_button.click()
        time.sleep(4)

        log(f"NC SUCCESS → {new_name} for thread {thread_id}", important=True)
        state["changed"] += 1
        return True

    except Exception as e:
        log(f"NC FAILED for thread {thread_id}: {str(e)[:100]}")
        return False

def nc_loop():
    cycle = 0
    while state["running"]:
        log(f"NC CYCLE {cycle + 1} started")

        device = random.choice(DEVICES)
        log(f"Using device: {device['deviceName']} for this cycle")

        options = uc.ChromeOptions()
        options.add_argument("--headless=new")  # New headless mode for better stealth
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--window-size=1080,2400")
        options.add_argument(f"--user-agent={device['userAgent']}")
        options.add_experimental_option("mobileEmulation", device)
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)

        driver = uc.Chrome(options=options, version_main=130)  # Pin Chrome version for stability

        # Login process
        driver.get("https://www.instagram.com/")
        time.sleep(4)

        driver.add_cookie({
            "name": "sessionid",
            "value": cfg["sessionid"],
            "domain": ".instagram.com",
            "path": "/",
            "secure": True,
            "httpOnly": True,
            "sameSite": "None"
        })

        driver.get("https://www.instagram.com/direct/inbox/")
        time.sleep(8)

        # Strict login check
        page_source_lower = driver.page_source.lower()
        current_url = driver.current_url
        if "login" in current_url or "accounts/login" in current_url or "log in" in page_source_lower or "username" in page_source_lower:
            log("LOGIN FAILED – Redirected to login or login form detected (sessionid invalid/expired)", important=True)
        else:
            log("LOGIN SUCCESS – Direct inbox loaded successfully", important=True)

        # Rotate name
        name_index = cycle % len(cfg["names"])
        new_name = cfg["names"][name_index]

        for thread_id in cfg["thread_ids"]:
            success = change_group_name(driver, thread_id, new_name)
            if not success:
                log("Retrying same thread after 10s...")
                time.sleep(10)
                change_group_name(driver, thread_id, new_name)  # retry once

            time.sleep(5)

        cycle += 1
        log(f"Cycle completed. Waiting {cfg['nc_delay']} sec for next")

        driver.quit()
        gc.collect()
        gc.collect()
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
    cfg["sessionid"] = accounts_raw[0].split(":")[0].strip()
    cfg["thread_ids"] = [line.split(":")[1].strip() for line in accounts_raw if line.strip()]

    cfg["names"] = [n.strip() for n in request.form["names"].split("\n") if n.strip()]
    cfg["nc_delay"] = float(request.form.get("nc_delay", "60"))

    threading.Thread(target=nc_loop, daemon=True).start()
    log(f"STARTED NC LOOP WITH {len(cfg['thread_ids'])} GROUPS")

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
